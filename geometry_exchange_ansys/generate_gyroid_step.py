#!/usr/bin/env python3
"""
Parameterized Gyroid STEP generator (Network type: solid = φ > -t).
Domain: 25.4×25.4×110 mm, buffer 0~5 & 105~110, main 5~105 mm.
Output: STEP (and optional STL). Optionally fuse with empty duct.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

try:
    from skimage import measure
except ImportError:
    from scipy.ndimage import marching_cubes
    measure = type("M", (), {"marching_cubes": marching_cubes})()

# Fixed domain (mm)
OUTER_XY = 25.4
OUTER_Z = 110.0
WALL_MM = 1.0
INNER_XY = 23.4
BUF_MM = 5.0
MAIN_Z_START = 5.0
MAIN_Z_END = 105.0


def phi_gyroid_mm(X_mm, Y_mm, Z_mm, a_mm):
    """φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)."""
    k = 2.0 * np.pi / a_mm
    return (
        np.sin(k * X_mm) * np.cos(k * Y_mm)
        + np.sin(k * Y_mm) * np.cos(k * Z_mm)
        + np.sin(k * Z_mm) * np.cos(k * X_mm)
    )


def write_stl(path, verts, faces, name="gyroid"):
    with open(path, "w") as f:
        f.write(f"solid {name}\n")
        for i, j, k in faces:
            v0, v1, v2 = verts[i], verts[j], verts[k]
            n = np.cross(v1 - v0, v2 - v0)
            n = n / (np.linalg.norm(n) + 1e-12)
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n    outer loop\n")
            for v in [v0, v1, v2]:
                f.write(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {name}\n")


def main():
    ap = argparse.ArgumentParser(description="Gyroid Network STEP generator (φ > -t)")
    ap.add_argument("--a", type=float, default=5.0, help="Unit cell size [mm], 3~8")
    ap.add_argument("--t", type=float, default=0.3, help="Thickness parameter (solid = φ > -t), 0.05~0.5")
    ap.add_argument("--res", type=int, default=60, help="Marching cubes resolution, 30~120")
    ap.add_argument("--out", type=str, default="", help="Output STEP path (default: gyroid_network_a{n}_t{m}.step)")
    ap.add_argument("--with-duct", action="store_true", default=True, help="Fuse with empty duct (default: True)")
    ap.add_argument("--no-duct", action="store_false", dest="with_duct", help="Do not add duct")
    ap.add_argument("--buffer", type=float, default=5.0, help="Buffer length [mm] at inlet/outlet")
    ap.add_argument("--stl", type=str, default="", help="Also save STL to this path for visual verification (same mesh as STEP)")
    ap.add_argument("--stl-only", action="store_true", help="Only write STL (no FreeCAD/STEP); use for quick visual check when FreeCAD unavailable")
    args = ap.parse_args()

    a = max(3.0, min(8.0, args.a))
    t = max(0.05, min(0.5, args.t))
    res = max(30, min(120, args.res))
    base_dir = Path(__file__).resolve().parent

    if args.out:
        step_path = Path(args.out)
    else:
        step_path = base_dir / f"gyroid_network_a{int(a)}_t{int(round(t*10)):02d}.step"
    step_path = step_path.resolve()

    # Main section only (buffer excluded)
    x_min, x_max = WALL_MM, WALL_MM + INNER_XY
    y_min, y_max = WALL_MM, WALL_MM + INNER_XY
    z_min, z_max = MAIN_Z_START, MAIN_Z_END
    n_cells = res
    x = np.linspace(x_min, x_max, n_cells + 1)
    y = np.linspace(y_min, y_max, n_cells + 1)
    z = np.linspace(z_min, z_max, n_cells + 1)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    phi = phi_gyroid_mm(X, Y, Z, a)

    # Network: solid = φ > -t  => isosurface at level = -t
    level = -t
    verts, faces, _, _ = measure.marching_cubes(phi, level=level)
    # Vertices are in index space; convert to mm
    dx = (x_max - x_min) / n_cells
    dy = (y_max - y_min) / n_cells
    dz = (z_max - z_min) / n_cells
    verts[:, 0] = verts[:, 0] * dx + x_min
    verts[:, 1] = verts[:, 1] * dy + y_min
    verts[:, 2] = verts[:, 2] * dz + z_min

    stl_saved = None
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        tmp_stl = tmp.name
    try:
        write_stl(tmp_stl, verts, faces, name="gyroid_network")
        if args.stl:
            stl_saved = Path(args.stl).resolve()
            shutil.copy2(tmp_stl, stl_saved)
        if args.stl_only:
            if not args.stl:
                stl_saved = base_dir / f"gyroid_network_a{int(a)}_t{int(round(t*10)):02d}_vis.stl"
                shutil.copy2(tmp_stl, stl_saved)
            print("[STL만 생성 완료] FreeCAD 미사용. STEP은 생성되지 않음.")
        else:
            duct_step = base_dir / "empty_duct_v32.step" if args.with_duct else None
            env = os.environ.copy()
            env["STL_PATH"] = tmp_stl
            env["STEP_PATH"] = str(step_path)
            if duct_step and duct_step.exists():
                env["DUCT_PATH"] = str(duct_step)
            run_script = base_dir / "stl_to_step_freecad.py"
            cmd = ["freecadcmd", "-c", f"exec(open({repr(str(run_script))}).read())"]
            ret = subprocess.run(cmd, env=env, cwd=str(base_dir), capture_output=True, text=True, timeout=900)
            if ret.returncode != 0:
                print(ret.stderr or ret.stdout, file=sys.stderr)
                sys.exit(1)
    finally:
        if os.path.isfile(tmp_stl):
            os.unlink(tmp_stl)

    # Log
    n_faces = len(faces)
    eps_approx = 0.5 + t / 3.0
    bbox = f"25.4 × 25.4 × 110.0 mm"
    if not args.stl_only:
        size_kb = step_path.stat().st_size / 1024 if step_path.exists() else 0
        print("[생성 완료]")
        print(f"  파라미터: a={a}mm, t={t}, type=network")
        print(f"  수식: solid = φ(x,y,z) > -{t}")
        print(f"  공극률 ε: {eps_approx:.2f} (추정)")
        print(f"  bounding box: {bbox}")
        print(f"  면 수: {n_faces:,}")
        print(f"  파일: {step_path} ({size_kb:.1f} KB)")
    else:
        print(f"  파라미터: a={a}mm, t={t}, type=network")
        print(f"  면 수: {n_faces:,}")
        print(f"  bounding box: {bbox}")
    if stl_saved and stl_saved.exists():
        print(f"  STL (시각검증용): {stl_saved} ({stl_saved.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

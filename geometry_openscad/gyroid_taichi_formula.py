#!/usr/bin/env python3
"""
Taichi LBM init_structure()와 동일한 수식으로 자이로이드 STL 생성.
옵션 --duct 로 외벽 STL을 불러와 자이로이드와 합쳐 최종 STL 한 파일로 출력 (검증용).

[Taichi 커널 로직과 일치]
- 외벽: x < 1.0 or x > 24.4 or y < 1.0 or y > 24.4 → Solid
- Main (5~105 mm): val = sin(k_g*x)*cos(k_g*y) + sin(k_g*y)*cos(k_g*z) + sin(k_g*z)*cos(k_g*x)
                   val > t_level → Solid. k_g = 2*pi/a (a = 주기 [mm])
"""
import numpy as np
from pathlib import Path

try:
    from skimage import measure
except ImportError:
    from scipy.ndimage import marching_cubes
    measure = type("M", (), {"marching_cubes": marching_cubes})()

# Taichi와 동일한 경계 (mm)
WALL_MM = 1.0
INNER_MAX_XY = 24.4   # 1 + 23.4
MAIN_Z_START = 5.0
MAIN_Z_END = 105.0
OUTER_XY = 25.4
OUTER_Z = 110.0
T_LEVEL_DEFAULT = 0.768


def gyroid_scalar_mm(X_mm, Y_mm, Z_mm, k_g):
    """Taichi와 동일: val = sin(k_g*x)*cos(k_g*y) + sin(k_g*y)*cos(k_g*z) + sin(k_g*z)*cos(k_g*x). x,y,z in mm."""
    return (
        np.sin(k_g * X_mm) * np.cos(k_g * Y_mm)
        + np.sin(k_g * Y_mm) * np.cos(k_g * Z_mm)
        + np.sin(k_g * Z_mm) * np.cos(k_g * X_mm)
    )


def load_stl_verts_faces(path):
    """ASCII STL을 읽어 verts (N,3), faces (F,3) 반환."""
    path = Path(path)
    verts_list = []
    faces_list = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                verts_list.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith("endloop") and len(verts_list) >= 3:
                n = len(verts_list)
                faces_list.append([n - 3, n - 2, n - 1])
    if not verts_list or not faces_list:
        raise ValueError(f"No geometry in {path}")
    return np.array(verts_list, dtype=np.float64), np.array(faces_list, dtype=np.int64)


def write_stl(path, verts, faces, solid_name="gyroid_taichi_formula"):
    with open(path, "w") as f:
        f.write(f"solid {solid_name}\n")
        for i, j, k in faces:
            v0, v1, v2 = verts[i], verts[j], verts[k]
            n = np.cross(v1 - v0, v2 - v0)
            n = n / (np.linalg.norm(n) + 1e-12)
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n    outer loop\n")
            for v in [v0, v1, v2]:
                f.write(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {solid_name}\n")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Taichi 수식 자이로이드 STL. --duct 로 외벽 포함 최종 STL 생성")
    ap.add_argument("--a", type=float, default=5.0, help="주기 a [mm], k_g = 2*pi/a")
    ap.add_argument("--t_level", type=float, default=T_LEVEL_DEFAULT, help="val > t_level 이면 Solid")
    ap.add_argument("--res", type=int, default=80, help="Marching cubes 해상도 (한 축당 셀 수)")
    ap.add_argument("--out", type=str, default="gyroid_taichi_formula.stl", help="최종 출력 STL")
    ap.add_argument("--duct", type=str, default="", help="외벽 STL 경로. 지정 시 이 메쉬와 자이로이드를 합쳐 --out 에 저장")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    duct_path = Path(args.duct) if args.duct else script_dir / "empty_duct_v32.stl"

    k_g = 2.0 * np.pi / args.a

    # 격자: 자이로이드만. 메인 구간 [1,24.4] x [1,24.4] x [5,105] + 여유로 닫힌 표면
    x_min, x_max = 0.5, 25.0
    y_min, y_max = 0.5, 25.0
    z_min, z_max = 4.0, 106.0
    nx = int((x_max - x_min) * args.res / 25.4)
    ny = int((y_max - y_min) * args.res / 25.4)
    nz = int((z_max - z_min) * args.res / 25.4)
    nx, ny, nz = max(nx, 20), max(ny, 20), max(nz, 20)
    x = np.linspace(x_min, x_max, nx, endpoint=False) + (x_max - x_min) / nx / 2
    y = np.linspace(y_min, y_max, ny, endpoint=False) + (y_max - y_min) / ny / 2
    z = np.linspace(z_min, z_max, nz, endpoint=False) + (z_max - z_min) / nz / 2
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    # Taichi와 동일: 메인 내부(1 <= x <= 24.4, 1 <= y <= 24.4, 5 <= z <= 105) 에서만 val > t_level → Solid
    in_main = (
        (X >= WALL_MM) & (X <= INNER_MAX_XY) & (Y >= WALL_MM) & (Y <= INNER_MAX_XY)
        & (Z >= MAIN_Z_START) & (Z <= MAIN_Z_END)
    )
    val = gyroid_scalar_mm(X, Y, Z, k_g)
    gyroid_solid = in_main & (val > args.t_level)

    level_set = np.where(gyroid_solid, -1.0, 1.0).astype(np.float64)

    spacing = ((x_max - x_min) / nx, (y_max - y_min) / ny, (z_max - z_min) / nz)
    verts, faces, _, _ = measure.marching_cubes(level_set, level=0, spacing=spacing)
    verts[:, 0] = verts[:, 0] + x_min
    verts[:, 1] = verts[:, 1] + y_min
    verts[:, 2] = verts[:, 2] + z_min

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if duct_path.exists():
        print(f"Loading duct: {duct_path}")
        duct_verts, duct_faces = load_stl_verts_faces(duct_path)
        n_duct = len(duct_verts)
        combined_verts = np.vstack([duct_verts, verts])
        combined_faces = np.vstack([duct_faces, faces + n_duct])
        write_stl(out_path, combined_verts, combined_faces, solid_name="gyroid_duct_v32")
        print(f"Saved {out_path}  (외벽 + 자이로이드, k_g=2*pi/{args.a}, t_level={args.t_level})")
    else:
        write_stl(out_path, verts, faces)
        print(f"Saved {out_path}  (gyroid only; --duct {duct_path} 없어 외벽 미포함)")


if __name__ == "__main__":
    main()

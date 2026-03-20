#!/usr/bin/env python3
"""
Generate STL files for all 3 geometry types (visual verification).
Voxel-based marching cubes approach — consistent with Taichi LBM geometry.

Output:
  empty_duct.stl          — 25.4×25.4×110 mm, wall 1 mm, hollow interior
  reference_6x6.stl       — 6×6 channels + inlet/outlet buffer
  gyroid_with_duct.stl     — Network gyroid (a=5, t=0.3) + 1 mm outer wall + buffer
"""
import argparse
from pathlib import Path

import numpy as np

try:
    from skimage import measure
except ImportError:
    from scipy.ndimage import marching_cubes
    measure = type("M", (), {"marching_cubes": marching_cubes})()

# Domain (mm)
OUTER_XY = 25.4
OUTER_Z = 110.0
WALL_MM = 1.0
INNER_XY = 23.4  # 25.4 - 2*1.0
MAIN_Z_START = 5.0
MAIN_Z_END = 105.0

# Reference 6×6
WALL_INNER = 1.0
N_CHAN = 6
CHANNEL_W = (INNER_XY - (N_CHAN - 1) * WALL_INNER) / N_CHAN
PERIOD = CHANNEL_W + WALL_INNER


def write_stl_binary(path, verts, faces, name="geometry"):
    """Write binary STL (much smaller files than ASCII)."""
    import struct
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(faces)))
        for tri in faces:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            n = np.cross(v1 - v0, v2 - v0)
            norm = np.linalg.norm(n)
            if norm > 1e-12:
                n /= norm
            f.write(struct.pack("<fff", *n))
            for v in [v0, v1, v2]:
                f.write(struct.pack("<fff", *v))
            f.write(struct.pack("<H", 0))


def voxel_to_stl(solid, dx_mm, dy_mm, dz_mm, origin, out_path, name="geometry"):
    """Run marching cubes on a binary voxel field and save STL."""
    verts, faces, _, _ = measure.marching_cubes(solid.astype(np.float32), level=0.5)
    verts[:, 0] = verts[:, 0] * dx_mm + origin[0]
    verts[:, 1] = verts[:, 1] * dy_mm + origin[1]
    verts[:, 2] = verts[:, 2] * dz_mm + origin[2]
    write_stl_binary(out_path, verts, faces, name)
    return len(faces)


def make_empty_duct(res):
    """25.4×25.4×110 mm duct, wall 1 mm, open both ends (Z direction fluid path)."""
    nx = int(round(OUTER_XY / res))
    ny = nx
    nz = int(round(OUTER_Z / res))
    dx = OUTER_XY / nx
    dy = OUTER_XY / ny
    dz = OUTER_Z / nz
    wall_v = max(1, int(round(WALL_MM / dx)))

    solid = np.zeros((nx, ny, nz), dtype=np.int32)
    for i in range(nx):
        for j in range(ny):
            if i < wall_v or i >= nx - wall_v or j < wall_v or j >= ny - wall_v:
                solid[i, j, :] = 1
    return solid, dx, dy, dz


def make_reference_6x6(res):
    """6×6 channels in main section, buffer regions are hollow duct."""
    nx = int(round(OUTER_XY / res))
    ny = nx
    nz = int(round(OUTER_Z / res))
    dx = OUTER_XY / nx
    dy = OUTER_XY / ny
    dz = OUTER_Z / nz
    wall_v = max(1, int(round(WALL_MM / dx)))
    z_main_start = int(round(MAIN_Z_START / dz))
    z_main_end = int(round(MAIN_Z_END / dz))

    solid = np.zeros((nx, ny, nz), dtype=np.int32)

    for i in range(nx):
        x_mm = (i + 0.5) * dx
        for j in range(ny):
            y_mm = (j + 0.5) * dy
            is_outer_wall = (x_mm < WALL_MM or x_mm > OUTER_XY - WALL_MM or
                             y_mm < WALL_MM or y_mm > OUTER_XY - WALL_MM)
            if is_outer_wall:
                solid[i, j, :] = 1
                continue

            x_inner = x_mm - WALL_MM
            y_inner = y_mm - WALL_MM
            cx = int(x_inner / PERIOD)
            cy = int(y_inner / PERIOD)
            x_in_cell = x_inner - cx * PERIOD
            y_in_cell = y_inner - cy * PERIOD
            is_channel = (x_in_cell < CHANNEL_W and y_in_cell < CHANNEL_W
                          and cx < N_CHAN and cy < N_CHAN)

            for k in range(nz):
                in_main = z_main_start <= k < z_main_end
                if in_main and not is_channel:
                    solid[i, j, k] = 1

    return solid, dx, dy, dz


def phi_gyroid(X_mm, Y_mm, Z_mm, a_mm):
    k = 2.0 * np.pi / a_mm
    return (np.sin(k * X_mm) * np.cos(k * Y_mm)
            + np.sin(k * Y_mm) * np.cos(k * Z_mm)
            + np.sin(k * Z_mm) * np.cos(k * X_mm))


def make_gyroid_with_duct(res, a=5.0, t=0.3):
    """Gyroid Network + outer wall + buffer (matching Taichi LBM geometry)."""
    nx = int(round(OUTER_XY / res))
    ny = nx
    nz = int(round(OUTER_Z / res))
    dx = OUTER_XY / nx
    dy = OUTER_XY / ny
    dz = OUTER_Z / nz

    x = np.arange(nx) * dx + 0.5 * dx
    y = np.arange(ny) * dy + 0.5 * dy
    z = np.arange(nz) * dz + 0.5 * dz
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    is_wall = ((X < WALL_MM) | (X > OUTER_XY - WALL_MM) |
               (Y < WALL_MM) | (Y > OUTER_XY - WALL_MM))
    in_buffer = (Z < MAIN_Z_START) | (Z > MAIN_Z_END)
    in_main = ~is_wall & ~in_buffer

    phi = phi_gyroid(X, Y, Z, a)
    gyroid_solid = in_main & (phi > -t)

    solid = np.where(is_wall | gyroid_solid, 1, 0).astype(np.int32)
    return solid, dx, dy, dz


def main():
    ap = argparse.ArgumentParser(description="Generate all 3 geometry STLs for visual verification")
    ap.add_argument("--res", type=float, default=0.5, help="Voxel size [mm] (smaller = finer, default 0.5)")
    ap.add_argument("--a", type=float, default=5.0, help="Gyroid unit cell [mm]")
    ap.add_argument("--t", type=float, default=0.3, help="Gyroid thickness param")
    ap.add_argument("--types", nargs="*", default=["duct", "6x6", "gyroid"],
                    choices=["duct", "6x6", "gyroid"],
                    help="Which geometry types to generate")
    ap.add_argument("--outdir", type=str, default="", help="Output directory (default: script dir)")
    args = ap.parse_args()

    out = Path(args.outdir) if args.outdir else Path(__file__).resolve().parent
    out = out.resolve()
    res = max(0.2, min(2.0, args.res))

    print(f"[설정] voxel={res}mm, domain=25.4×25.4×110mm, wall=1mm")
    print(f"  gyroid: a={args.a}mm, t={args.t}, type=network (φ > -{args.t})")
    print()

    if "duct" in args.types:
        solid, dx, dy, dz = make_empty_duct(res)
        p = out / "empty_duct.stl"
        nf = voxel_to_stl(solid, dx, dy, dz, (0, 0, 0), p, "empty_duct")
        print(f"  [빈 덕트] {p.name}: voxel {solid.shape}, 면 {nf:,}, {p.stat().st_size/1024:.0f} KB")

    if "6x6" in args.types:
        solid, dx, dy, dz = make_reference_6x6(res)
        p = out / "reference_6x6.stl"
        nf = voxel_to_stl(solid, dx, dy, dz, (0, 0, 0), p, "reference_6x6")
        print(f"  [6×6 채널] {p.name}: voxel {solid.shape}, 면 {nf:,}, {p.stat().st_size/1024:.0f} KB")

    if "gyroid" in args.types:
        solid, dx, dy, dz = make_gyroid_with_duct(res, args.a, args.t)
        p = out / "gyroid_with_duct.stl"
        nf = voxel_to_stl(solid, dx, dy, dz, (0, 0, 0), p, "gyroid_with_duct")
        eps = 1.0 - solid.sum() / solid.size
        print(f"  [자이로이드+덕트] {p.name}: voxel {solid.shape}, 면 {nf:,}, "
              f"공극률 {eps:.3f}, {p.stat().st_size/1024:.0f} KB")

    print("\n[완료] 메쉬뷰어(MeshLab, Blender, Windows 3D Viewer)로 확인하세요.")


if __name__ == "__main__":
    main()

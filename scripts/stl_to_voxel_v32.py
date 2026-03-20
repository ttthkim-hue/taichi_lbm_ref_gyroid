#!/usr/bin/env python3
"""
V3.2 STL → Voxel (.npy) for LBM
- STL 메쉬를 로드하여 격자 셀 중심이 고체 내부인지 판별 → 1=solid, 0=fluid
- [공통] 외부 25.4×25.4 mm, 길이 110 mm, dx=0.2 mm → 127×127×550
"""
import numpy as np
from pathlib import Path

try:
    import trimesh
except ImportError:
    trimesh = None

DX_MM = 0.2
OUTER_XY_MM = 25.4
OUTER_Z_MM = 110.0
NX = NY = int(OUTER_XY_MM / DX_MM)
NZ = int(OUTER_Z_MM / DX_MM)


def stl_to_mask(stl_path: str, nx: int = NX, ny: int = NY, nz: int = NZ, dx_mm: float = DX_MM) -> np.ndarray:
    """
    STL 파일을 voxel mask로 변환. 1=고체, 0=유체.
    셀 중심 좌표 (mm)에서 메쉬 내부 여부로 판단. trimesh 필요.
    """
    if trimesh is None:
        raise SystemExit("Install trimesh for voxelization: python3 -m venv .venv_v32 && .venv_v32/bin/pip install trimesh")
    mesh = trimesh.load(stl_path)
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = mesh[0] if hasattr(mesh, "__getitem__") else list(mesh.geometry.values())[0]

    i = np.arange(nx, dtype=np.float64)
    j = np.arange(ny, dtype=np.float64)
    k = np.arange(nz, dtype=np.float64)
    x = (i + 0.5) * dx_mm
    y = (j + 0.5) * dx_mm
    z = (k + 0.5) * dx_mm
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    inside = mesh.contains(points)
    mask = inside.astype(np.uint8).reshape(nx, ny, nz)
    return mask


def main():
    import argparse
    ap = argparse.ArgumentParser(description="V3.2 STL to voxel .npy for LBM (127×127×550). Multiple STLs → union (solid = inside any).")
    ap.add_argument("stl", type=str, nargs="+", help="Input STL path(s); multiple = union in voxel space")
    ap.add_argument("-o", "--out", type=str, default=None, help="Output .npy path")
    ap.add_argument("--nx", type=int, default=NX)
    ap.add_argument("--ny", type=int, default=NY)
    ap.add_argument("--nz", type=int, default=NZ)
    ap.add_argument("--dx", type=float, default=DX_MM)
    args = ap.parse_args()

    out = args.out or Path(args.stl[0]).with_suffix(".npy")
    mask = None
    for p in args.stl:
        print(f"Loading {p} ...")
        m = stl_to_mask(p, args.nx, args.ny, args.nz, args.dx)
        mask = m if mask is None else np.maximum(mask, m)
    np.save(out, mask)
    print(f"Saved {out}  shape={mask.shape}  solid_frac={mask.mean():.4f}")


if __name__ == "__main__":
    main()

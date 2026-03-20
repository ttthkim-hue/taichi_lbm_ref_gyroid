#!/usr/bin/env python3
"""
V3.2 자이로이드 덕트 마스크를 Taichi init_structure()와 동일한 수식으로 생성.
- 검증: 이 .npy와 STL→voxel .npy를 비교하면 수식/STL 일치 여부 확인 가능.
- 사용: taichi_lbm_solver_v3.py --mask gyroid_duct_v32_formula.npy ...

[규칙] STL/문서와 동일
- dx=0.2 mm, 127×127×550 (25.4×25.4×110 mm)
- 셀 중심: x=(i+0.5)*dx, y=(j+0.5)*dx, z=(k+0.5)*dx (mm)
- 외벽: x<1 or x>24.4 or y<1 or y>24.4 → 1
- 버퍼: z<5 or z>105 → 0
- Main: val = sin(k_g*x)*cos(k_g*y)+... , val>t_level → 1
"""
import numpy as np
from pathlib import Path

DX_MM = 0.2
OUTER_XY_MM = 25.4
OUTER_Z_MM = 110.0
NX = NY = int(round(OUTER_XY_MM / DX_MM))  # 127
NZ = int(round(OUTER_Z_MM / DX_MM))         # 550

WALL_MM = 1.0
INNER_MAX_XY = 24.4
MAIN_Z_START = 5.0
MAIN_Z_END = 105.0
T_LEVEL_DEFAULT = 0.768


def gyroid_scalar(x_mm, y_mm, z_mm, k_g):
    return (
        np.sin(k_g * x_mm) * np.cos(k_g * y_mm)
        + np.sin(k_g * y_mm) * np.cos(k_g * z_mm)
        + np.sin(k_g * z_mm) * np.cos(k_g * x_mm)
    )


def build_mask_numpy(a_mm: float = 5.0, t_level: float = T_LEVEL_DEFAULT) -> np.ndarray:
    """Taichi init_structure()와 동일 로직으로 mask (1=solid, 0=fluid) 생성. 벡터화."""
    k_g = 2.0 * np.pi / a_mm
    i = np.arange(NX, dtype=np.float64)
    j = np.arange(NY, dtype=np.float64)
    k = np.arange(NZ, dtype=np.float64)
    x = (i + 0.5) * DX_MM
    y = (j + 0.5) * DX_MM
    z = (k + 0.5) * DX_MM
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    is_wall = (X < WALL_MM) | (X > INNER_MAX_XY) | (Y < WALL_MM) | (Y > INNER_MAX_XY)
    in_buffer = (Z < MAIN_Z_START) | (Z > MAIN_Z_END)
    in_main = ~is_wall & ~in_buffer
    val = gyroid_scalar(X, Y, Z, k_g)
    gyroid_solid = in_main & (val > t_level)

    mask = np.where(is_wall | gyroid_solid, 1, 0).astype(np.int32)
    return mask


def main():
    import argparse
    ap = argparse.ArgumentParser(description="V3.2 자이로이드 덕트 마스크 (수식) 생성")
    ap.add_argument("--a", type=float, default=5.0, help="주기 a [mm]")
    ap.add_argument("--t_level", type=float, default=T_LEVEL_DEFAULT)
    ap.add_argument("-o", "--out", type=str, default="gyroid_duct_v32_formula.npy")
    ap.add_argument("--compare", type=str, default=None, help="STL voxel .npy와 비교")
    args = ap.parse_args()

    print(f"Building mask {NX}×{NY}×{NZ}  dx={DX_MM} mm  a={args.a}  t_level={args.t_level}")
    mask = build_mask_numpy(a_mm=args.a, t_level=args.t_level)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, mask)
    sf = mask.mean()
    print(f"Saved {out}  solid_frac={sf:.4f}")

    if args.compare:
        other = np.load(args.compare).astype(np.int32)
        if other.shape != mask.shape:
            print(f"  Compare: shape mismatch {other.shape} vs {mask.shape}")
        else:
            diff = (mask != other).sum()
            print(f"  Compare with {args.compare}: diff cells = {diff}  (match: {diff == 0})")


if __name__ == "__main__":
    main()

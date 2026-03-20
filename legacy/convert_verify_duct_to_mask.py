from __future__ import annotations

"""
verify_duct_nowall.dat (MN 포맷) → Taichi LBM v3용 mask .npy 변환 스크립트.

MN convention:
  1: fluid
  2: solid
  3: inlet
  4: outlet

Taichi v3 마스크 규약:
  0: fluid
  1: solid
"""

import argparse
from pathlib import Path

import numpy as np

from geometry_io import read_mn_dat


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dat",
        type=str,
        required=True,
        help="OpenLB MN .dat path (e.g. verify_duct_nowall.dat)",
    )
    ap.add_argument(
        "--out",
        type=str,
        default="verify_duct_nowall_mask.npy",
        help="Output .npy path for Taichi mask (solid=1, fluid=0)",
    )
    args = ap.parse_args()

    geom = read_mn_dat(args.dat)
    # MN=2를 solid=1, 나머지(1,3,4)는 fluid=0으로 처리
    mask = (geom.mn == 2).astype(np.int32)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, mask)

    solid_fraction = float(mask.mean())
    print(f"Saved mask to {out_path}")
    print(f"  Grid: {geom.nx} x {geom.ny} x {geom.nz}")
    print(f"  Solid fraction: {solid_fraction:.4f}")


if __name__ == "__main__":
    main()


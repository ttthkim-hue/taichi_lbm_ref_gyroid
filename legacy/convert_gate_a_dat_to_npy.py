#!/usr/bin/env python3
"""
OpenLB gate_a MN .dat → Taichi LBM mask .npy 변환.
MN 2=solid → 1, 그 외(1,3,4)=fluid → 0.
"""
import argparse
import sys
from pathlib import Path

# geometry_io는 taichi_lbm_ref_gyroid에 있음
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry_io import read_mn_dat

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dat", help="e.g. openlb_gyroid/results/gate_a/ref_dx02.dat")
    ap.add_argument("-o", "--out", default=None, help="Output .npy path (default: same name with .npy)")
    args = ap.parse_args()
    p = Path(args.dat)
    if not p.is_file():
        raise SystemExit(f"Not found: {p}")
    geom = read_mn_dat(p)
    mask = (geom.mn == 2).astype("int32")
    out = Path(args.out) if args.out else p.with_suffix(".npy")
    out.parent.mkdir(parents=True, exist_ok=True)
    import numpy as np
    np.save(out, mask)
    print(f"Saved {out} shape={mask.shape} solid_frac={mask.mean():.4f}")

if __name__ == "__main__":
    main()

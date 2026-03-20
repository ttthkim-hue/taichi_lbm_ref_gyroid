#!/usr/bin/env python3
"""plan_1.9V §2.3: L1 빠른 재확인 — 5000 step만 실행, ΔP ≈ 0.070 확인 (dt 고정 후)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMWrapper

def main():
    nx, ny, nz = 127, 127, 550
    dx = 0.0002
    nu_phys = 3.52e-5
    rho_phys = 0.746
    u_in = 0.2778
    wall_voxels = 5
    buf_cells = 2

    voxel = np.zeros((nx, ny, nz), dtype=np.int32)
    voxel[:wall_voxels, :, :] = 1
    voxel[nx - wall_voxels:, :, :] = 1
    voxel[:, :wall_voxels, :] = 1
    voxel[:, ny - wall_voxels:, :] = 1

    try:
        w = TaichiLBMWrapper(nx, ny, nz, dx, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=buf_cells, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(nx, ny, nz, dx, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=buf_cells, arch=ti.cpu)
    w.set_geometry_from_voxel(voxel)

    steps = 5000
    print(f"[plan_1.9V §2.3] L1 빠른 재확인: {steps} step")
    dp, _, log = w.run_with_logging(max_steps=steps, log_interval=1000, verbose=True)
    print(f"\n[결과] step {steps}  ΔP_sim = {dp:.6f} Pa  (목표: ΔP ≈ 0.070)")
    ok = 0.05 <= dp <= 0.09
    print(f"판정: {'PASS' if ok else 'CHECK'} (0.05~0.09 Pa 구간)")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())

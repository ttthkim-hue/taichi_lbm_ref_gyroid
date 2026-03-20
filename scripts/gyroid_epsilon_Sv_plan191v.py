#!/usr/bin/env python3
"""
plan_1.91V §3.2: Gyroid 기준 케이스 (a=5 mm, t=0.3) ε·S_v 실측.
131×131×550, dx=0.2mm. 커널 생성 후 내부 공극률 ε 및 비표면적 S_v [1/m] 출력.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMCore

NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
DX = DX_MM * 1e-3
WALL_VOXELS = 5
A_MM = 5.0
T = 0.3


def main():
    try:
        core = TaichiLBMCore(NX, NY, NZ, DX, 3.52e-5, 0.746, 0.2778, periodic_z=False, body_force_z=0.0, arch=ti.cuda)
    except Exception:
        core = TaichiLBMCore(NX, NY, NZ, DX, 3.52e-5, 0.746, 0.2778, periodic_z=False, body_force_z=0.0, arch=ti.cpu)
    core.set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS)
    solid_np = core.solid.to_numpy()

    w = WALL_VOXELS
    interior = solid_np[w:NX - w, w:NY - w, w:NZ - w]
    n_total = interior.size
    n_solid = int(interior.sum())
    n_fluid = n_total - n_solid
    eps = n_fluid / n_total if n_total > 0 else 0.0

    fluid_np = (solid_np == 0)
    solid_np_bool = (solid_np == 1)
    interface_faces = 0
    for axis, shift in [(0, -1), (0, 1), (1, -1), (1, 1), (2, -1), (2, 1)]:
        interface_faces += np.sum(solid_np_bool & np.roll(fluid_np, shift, axis=axis))
    area_m2 = interface_faces * (DX ** 2)
    vol_fluid_m3 = n_fluid * (DX ** 3)
    S_v = area_m2 / (vol_fluid_m3 + 1e-30)  # 1/m

    print(f"[plan_1.91V §3.2] Gyroid a={A_MM} mm, t={T}")
    print(f"  격자 = {NX}×{NY}×{NZ}, dx = {DX_MM} mm")
    print(f"  ε (공극률) = {eps:.4f}")
    print(f"  S_v (비표면적) = {S_v:.2f} 1/m")
    print(f"  유체 셀 수 = {n_fluid}, 경계면 셀 수 = {interface_faces}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

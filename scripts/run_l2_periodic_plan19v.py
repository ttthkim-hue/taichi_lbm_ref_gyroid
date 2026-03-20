#!/usr/bin/env python3
"""
plan_1.9V §3.3 / plan_1.91V §2.2: L2 Reference 6×6 주기BC + 체적력 검증.
131격자, ΔP_target=3.819 Pa. 검증: u_mean(유체 평균) vs u_channel_theory=0.449 m/s ±5%.
plan_1.91V §2.3: K_sim = u_superficial × μ × L / ΔP 출력.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMWrapper

WALL_VOXELS = 5
DX_MM = 0.2
NX, NY, NZ = 131, 131, 550
DX = DX_MM * 1e-3
BUF_CELLS = 2
CHANNEL_MM = 3.2
INNER_MM = 24.2
L_PHYS = 0.11  # m
# plan_1.91V §2.2: 채널 유속으로 비교 (덕트 표면유속 0.2778 아님)
U_CHANNEL_TARGET = 0.449  # m/s (이론 채널 유속)
DP_TARGET = 3.819
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS  # Pa·s
A_DUCT_PHYS = (INNER_MM * 1e-3) ** 2  # m²


def make_ref6x6_131():
    voxel = np.zeros((NX, NY, NZ), dtype=np.int32)
    for b in [0, 1]:
        voxel[:WALL_VOXELS if b == 0 else NX - WALL_VOXELS, :, :] = 1
        voxel[:, :WALL_VOXELS if b == 0 else NY - WALL_VOXELS, :] = 1
        voxel[:, :, :WALL_VOXELS if b == 0 else NZ - WALL_VOXELS] = 1
    ch_ranges = [(5, 21), (26, 42), (47, 63), (68, 84), (89, 105), (110, 126)]
    for i in range(WALL_VOXELS, NX - WALL_VOXELS):
        for j in range(WALL_VOXELS, NY - WALL_VOXELS):
            in_ch = any(lo <= i < hi for lo, hi in ch_ranges) and any(lo <= j < hi for lo, hi in ch_ranges)
            voxel[i, j, :] = 0 if in_ch else 1
    return voxel


def main():
    voxel = make_ref6x6_131()
    try:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS, u_in_phys=U_CHANNEL_TARGET,
                            mode="periodic_body_force", buf_cells=BUF_CELLS, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS, u_in_phys=U_CHANNEL_TARGET,
                            mode="periodic_body_force", buf_cells=BUF_CELLS, arch=ti.cpu)
    w.set_geometry_from_voxel(voxel)
    w.set_body_force(DP_TARGET, L_PHYS)

    z_mid = NZ // 2
    max_steps = 100_000
    log_interval = 1000
    K_sim = 0.0
    print(f"[plan_1.91V §2.2] L2 주기BC: ΔP_target={DP_TARGET} Pa, u_channel_theory={U_CHANNEL_TARGET} m/s")
    for step in range(0, max_steps, log_interval):
        for _ in range(log_interval):
            w.core.step()
        Q_lb = w.core.get_flux_z(z_mid)
        rho_np = w.core.rho.to_numpy()
        mask_z = voxel[:, :, z_mid] == 0
        rho_sum_z = (rho_np[:, :, z_mid] * mask_z).sum()
        u_mean_lb = Q_lb / (rho_sum_z + 1e-30)
        dt = w.core.dt
        u_channel_phys = u_mean_lb * DX / dt
        # Darcy: u_superficial = Q/(A_duct), Q_phys = Q_lb*dx^3/dt
        Q_phys = float(Q_lb) * (DX ** 3) / dt
        u_superficial = Q_phys / A_DUCT_PHYS
        K_sim = u_superficial * MU_PHYS * L_PHYS / (DP_TARGET + 1e-30)
        err_pct = abs(u_channel_phys - U_CHANNEL_TARGET) / (U_CHANNEL_TARGET + 1e-30) * 100
        print(f"  {step + log_interval:6d}  u_channel={u_channel_phys:.4f} m/s  err={err_pct:.2f}%  K_sim={K_sim:.2e} m²")
        if step >= 5000 and err_pct < 5.0:
            print(f"  [PASS] u_mean vs u_channel_theory 오차 < 5%")
            print(f"  [L2-C] K_sim(B) = {K_sim:.2e} m² (Darcy: u_superficial×μ×L/ΔP)")
            print(f"  [결과] K_sim(B) = {K_sim:.4e} m²")
            return 0
    print("  [미수렴 또는 오차 > 5%]")
    print(f"  [L2-C] K_sim(B) = {K_sim:.2e} m²")
    print(f"  [결과] K_sim(B) = {K_sim:.4e} m²")
    return 1


if __name__ == "__main__":
    sys.exit(main())

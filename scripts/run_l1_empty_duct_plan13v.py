#!/usr/bin/env python3
"""
plan_1.3V §5 / plan_1.4V §1 / plan_1.5V §1: 빈 덕트 Level 1 본검증.
도메인 127×127×550, dx=0.2mm. 이론 ΔP = Shah & London 발달유동 상관식.
PASS: ΔP 오차 < 5%, Q 차이 < 1%, 질량 드리프트 < 0.1%, clips = 0 (4항목 모두).
"""
import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti

def main():
    nx, ny, nz = 127, 127, 550
    dx = 0.0002  # m
    nu_phys = 3.52e-5
    rho_phys = 0.746
    u_in = 0.2778
    wall_voxels = 5  # 1mm = 5*0.2mm
    buf_cells = 2

    # 빈 덕트: 경계 5 voxel만 벽
    voxel = np.zeros((nx, ny, nz), dtype=np.int32)
    voxel[:wall_voxels, :, :] = 1
    voxel[nx - wall_voxels:, :, :] = 1
    voxel[:, :wall_voxels, :] = 1
    voxel[:, ny - wall_voxels:, :] = 1

    # plan_1.4V §1: 실제 유체 영역으로 Dh 확정
    inner_xy = (nx - 2 * wall_voxels)  # 117
    Dh_m = inner_xy * dx  # 23.4 mm
    Re = u_in * Dh_m / nu_phys

    # plan_1.5V §1: 측정면 간 거리 (덕트 전체 아님). Wrapper와 동일 계산.
    z_in = buf_cells + 5
    z_out = nz - 1 - buf_cells - 5
    z_in = max(1, min(z_in, nz - 2))
    z_out = max(1, min(z_out, nz - 2))
    if z_out <= z_in:
        z_out = nz - 2
        z_in = 1
    L_measure = (z_out - z_in) * dx  # [m]
    # 검증: 측정면 간 거리 = (z_out - z_in) × dx. z_in=buf+5=7, z_out=nz-1-buf-5=542 → 535×0.2mm = 107 mm
    print(f"[L_measure 검증] z_in = {z_in}, z_out = {z_out}  →  L_measure = ({z_out} - {z_in}) × {dx*1000} mm = {L_measure*1000:.3f} mm (덕트 전체 110 mm 중 측정 구간)")

    # Shah & London 발달유동 상관식 (Fanning 관례 통일, 정사각 단면)
    # 완전 발달: f_fd_Re = 14.227 (Fanning, 정사각). Darcy면 56.91(=4×14.227).
    # 발달유동 상수: K_inf = 1.43, C = 0.00029 (정사각). 원형은 1.25, 0.00021.
    Lp = L_measure / (Dh_m * Re)
    sqrt_Lp = math.sqrt(Lp)
    f_app_Re = 3.44 / sqrt_Lp + (14.227 + 1.43 / (4 * Lp) - 3.44 / sqrt_Lp) / (1 + 0.00029 / (Lp * Lp))
    f_app = f_app_Re / Re
    # ΔP = 4×f_F × (L/Dh) × 0.5ρu² (Fanning f → Darcy 관례)
    dP_theory = 4 * f_app * (L_measure / Dh_m) * 0.5 * rho_phys * u_in ** 2

    # 기존 Darcy/원형 단면 기반 (비교 참고용)
    # f_fd_Re = 56.91  # Darcy (4×Fanning)
    # K_inf, C = 1.25, 0.00021  # 원형
    # f_app_Re_old = 3.44/sqrt_Lp + (56.91 + 1.25/(4*Lp) - 3.44/sqrt_Lp) / (1 + 0.00021/(Lp*Lp))
    # dP_theory_old = (f_app_Re_old/Re) * (L_measure/Dh_m) * 0.5 * rho_phys * u_in**2  # Darcy 식에 ×4 없음이면 Fanning 대비 1/4

    from solver.taichi_lbm_core import TaichiLBMWrapper

    try:
        w = TaichiLBMWrapper(nx, ny, nz, dx, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=buf_cells, arch=ti.cuda)
        arch = ti.cuda
    except Exception:
        w = TaichiLBMWrapper(nx, ny, nz, dx, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=buf_cells, arch=ti.cpu)
        arch = ti.cpu
    print("Arch:", arch)
    w.set_geometry_from_voxel(voxel)

    max_steps = 100_000
    print(f"Running up to {max_steps} steps (convergence → early stop)...")
    dp, converged, log = w.run_with_logging(max_steps=max_steps, log_interval=1000, verbose=True)

    # plan_1.5V §1.5: 4항목 PASS 기준
    err_pct = abs(dp - dP_theory) / (dP_theory + 1e-30) * 100.0
    pass_dp = err_pct < 5.0

    last_ = log[-1] if log else {}
    q_in, q_out = last_.get("Q_in", 0.0), last_.get("Q_out", 0.0)
    q_avg = (abs(q_in) + abs(q_out)) * 0.5 + 1e-30
    q_diff_pct = abs(q_in - q_out) / q_avg * 100.0
    pass_q = q_diff_pct < 1.0

    mass0 = log[0]["total_mass"] if log else 1.0
    mass_last = last_.get("total_mass", mass0)
    mass_drift_pct = abs(mass_last - mass0) / (mass0 + 1e-30) * 100.0
    pass_mass = mass_drift_pct < 0.1

    clips = last_.get("outlet_clips", 0)
    pass_clips = clips == 0

    pass_l1 = pass_dp and pass_q and pass_mass and pass_clips

    # plan_1.5V §1.4: 출력 형식
    print()
    print("[L1 검증 — 발달유동 상관식]")
    print(f"  Dh = {Dh_m*1000:.2f} mm, Re = {Re:.1f}")
    print(f"  L_measure = {L_measure*1000:.3f} mm, L⁺ = {Lp:.6f}")
    print(f"  f_app·Re = {f_app_Re:.4f}  (완전발달 극한 Fanning: 14.23)")
    print(f"  ΔP_theory (발달유동) = {dP_theory:.6f} Pa")
    print(f"  ΔP_sim = {dp:.6f} Pa")
    print(f"  오차 = {err_pct:.2f}%")
    print(f"  판정 = {'PASS' if pass_l1 else 'FAIL'} (기준: 오차 < 5%)")
    if not pass_l1:
        print(f"  [세부] ΔP:{pass_dp}, Q차이<1%:{pass_q}, 질량드리프트<0.1%:{pass_mass}, clips=0:{pass_clips}")
    return 0 if pass_l1 else 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
plan_1.7V §3.1 + §4 + §6: L2 Reference 6×6 재검증 (저유속 + 균등 분할).
- u_in = 0.0556 m/s (1/5) → Δρ_lbm ≈ 2% (LBM 비압축성 허용).
- NX=NY=131 → 채널 16 voxel 균등 분할 (96/6), CV 개선 목표.
- PASS: ΔP 오차 < 5%, Q < 1%, clips=0, CV < 10%.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti

# plan_1.7V §4: NX=NY=131 → 내부 121, 격벽 5×5=25, 채널 96 → 16 voxel/channel 균등
WALL_VOXELS = 5
DX_MM = 0.2
NX, NY, NZ = 131, 131, 550
INNER_CELLS = NX - 2 * WALL_VOXELS  # 121
CHANNEL_VOXELS = 16  # 96/6
CHANNEL_MM = CHANNEL_VOXELS * DX_MM  # 3.2 mm
INNER_MM = INNER_CELLS * DX_MM  # 24.2 mm
DH_MM = CHANNEL_MM
DX = DX_MM * 1e-3
BUF_CELLS = 2

# plan_1.7V §3.1: 저유속 → Δρ_lbm < 10% 목표. 131 격자에서 ΔP_theory ≈ 0.15 Pa 되도록 u_in 설정.
# (127 격자 1/5일 때 0.153 Pa; 131은 단면 커져서 동일 u_in이면 ΔP 더 큼 → u_in 추가 축소)
TARGET_DP_THEORY_PA = 0.153  # plan §3.1: 3.819×(1/5)²


def make_ref6x6_voxel_131():
    """6×6 균등 분할: 채널당 16 voxel. 구간 [5,21),[26,42),[47,63),[68,84),[89,105),[110,126)."""
    voxel = np.zeros((NX, NY, NZ), dtype=np.int32)
    voxel[:WALL_VOXELS, :, :] = 1
    voxel[NX - WALL_VOXELS:, :, :] = 1
    voxel[:, :WALL_VOXELS, :] = 1
    voxel[:, NY - WALL_VOXELS:, :] = 1
    voxel[:, :, :WALL_VOXELS] = 1
    voxel[:, :, NZ - WALL_VOXELS:] = 1
    # 6 channels × 16 + 5 walls × 5 = 121
    ch_ranges = [(5, 21), (26, 42), (47, 63), (68, 84), (89, 105), (110, 126)]
    for i in range(WALL_VOXELS, NX - WALL_VOXELS):
        for j in range(WALL_VOXELS, NY - WALL_VOXELS):
            in_ch_x = any(lo <= i < hi for lo, hi in ch_ranges)
            in_ch_y = any(lo <= j < hi for lo, hi in ch_ranges)
            if in_ch_x and in_ch_y:
                voxel[i, j, :] = 0
            else:
                voxel[i, j, :] = 1
    return voxel


def channel_id_ij_131():
    """(i,j) → 채널 0..35 (wall=-1). ch_ranges 동일."""
    ch_ranges = [(5, 21), (26, 42), (47, 63), (68, 84), (89, 105), (110, 126)]
    cid = np.full((NX, NY), -1, dtype=np.int32)
    for cy, (jy_lo, jy_hi) in enumerate(ch_ranges):
        for cx, (ix_lo, ix_hi) in enumerate(ch_ranges):
            c = cy * 6 + cx
            for i in range(ix_lo, ix_hi):
                for j in range(jy_lo, jy_hi):
                    if 0 <= i < NX and 0 <= j < NY:
                        cid[i, j] = c
    return cid


def main():
    voxel = make_ref6x6_voxel_131()
    cross_fluid = np.sum(voxel[WALL_VOXELS:NX - WALL_VOXELS, WALL_VOXELS:NY - WALL_VOXELS, NZ // 2] == 0)
    cross_total = (NX - 2 * WALL_VOXELS) * (NY - 2 * WALL_VOXELS)
    porosity_cross = cross_fluid / cross_total if cross_total > 0 else 0
    print(f"[6×6 마스크 plan_1.7V] NX=NY=131, 채널 16 voxel 균등. 단면 유체/전체 = {cross_fluid}/{cross_total} = {porosity_cross:.4f}")

    nu_phys = 3.52e-5
    rho_phys = 0.746
    area_duct_mm2 = INNER_MM * INNER_MM
    area_channel_mm2 = 36 * (CHANNEL_MM ** 2)
    Dh_m = DH_MM * 1e-3
    z_in = BUF_CELLS + 5
    z_out = NZ - 1 - BUF_CELLS - 5
    z_in = max(1, min(z_in, NZ - 2))
    z_out = max(1, min(z_out, NZ - 2))
    if z_out <= z_in:
        z_out = NZ - 2
        z_in = 1
    L_measure = (z_out - z_in) * DX
    # 131 격자에서 ΔP_theory = TARGET_DP_THEORY_PA 되도록 u_channel 역산 → u_in 설정 (저유속)
    u_channel_HP = TARGET_DP_THEORY_PA * (Dh_m ** 2) / (2.0 * 14.227 * nu_phys * L_measure * rho_phys)
    u_in = u_channel_HP * (area_channel_mm2 / area_duct_mm2)
    # plan_2.2V 수정 3: inlet BC는 유체 셀에만 u_in 적용 → 시뮬에서 채널 유속 = u_in. 이론 비교 시 u_channel = u_in 사용.
    u_channel = u_in
    Re_ch = u_channel * Dh_m / nu_phys
    Le_mm = 0.05 * Re_ch * DH_MM
    print(f"  채널 폭 = {CHANNEL_MM:.3f} mm, Dh = {DH_MM:.3f} mm")
    print(f"  u_in = u_channel (inlet 유체 전용) = {u_in:.4f} m/s, Re = {Re_ch:.1f}, Le = {Le_mm:.1f} mm")
    print(f"  시뮬 inlet BC: u_in = {u_in} m/s")

    from solver.taichi_lbm_core import TaichiLBMWrapper

    print(f"  L_measure = (z_out - z_in) × dx = {z_out - z_in} × {DX*1000} mm = {L_measure*1000:.3f} mm")

    # HP, Fanning. ΔP_theory = 4×f×(L/Dh)×0.5×ρ×u_channel², u_channel = u_in (plan_2.2V)
    f_Fanning_Re = 14.227
    f_Fanning = f_Fanning_Re / Re_ch
    dP_theory = 4 * f_Fanning * (L_measure / Dh_m) * 0.5 * rho_phys * u_channel ** 2
    p_scale_approx = rho_phys * (DX / (0.05 * DX / u_in)) ** 2 / 3.0
    drho_lbm_approx = dP_theory / (p_scale_approx + 1e-30)
    print(f"  ΔP_theory (HP, Fanning) = {dP_theory:.6f} Pa, Δρ/ρ 예상 ≈ {drho_lbm_approx*100:.1f}% (LBM 허용 목표)")

    try:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=BUF_CELLS, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=BUF_CELLS, arch=ti.cpu)
    w.set_geometry_from_voxel(voxel)

    max_steps = 100_000
    print(f"Running up to {max_steps} steps...")
    dp_sim, converged, log = w.run_with_logging(max_steps=max_steps, log_interval=1000, verbose=True)

    err_pct = abs(dp_sim - dP_theory) / (dP_theory + 1e-30) * 100
    pass_dp = err_pct < 5.0
    last_ = log[-1] if log else {}
    q_in, q_out = last_.get("Q_in", 0), last_.get("Q_out", 0)
    q_diff_pct = abs(q_in - q_out) / ((abs(q_in) + abs(q_out)) * 0.5 + 1e-30) * 100
    pass_q = q_diff_pct < 1.0
    clips = last_.get("outlet_clips", 0)
    pass_clips = clips == 0

    rho_np = w.core.rho.to_numpy()
    v_np = w.core.v.to_numpy()
    # plan_2.3V Phase 3: 수치 역산 진단 (ΔP 1/3 원인 추적, core와 동일 슬라이스)
    zi, zo = w.z_in, w.z_out
    mask_in = voxel[:, :, zi] == 0
    mask_out = voxel[:, :, zo] == 0
    n_fluid_in = int(mask_in.sum())
    n_fluid_out = int(mask_out.sum())
    mean_rho_in = float(rho_np[:, :, zi][mask_in].mean())
    mean_rho_out = float(rho_np[:, :, zo][mask_out].mean())
    delta_rho_lbm = mean_rho_in - mean_rho_out
    p_scale = float(w.core.p_scale)
    delta_P_from_rho = delta_rho_lbm * p_scale
    rho_center_in = float(rho_np[65, 65, zi]) if voxel[65, 65, zi] == 0 else np.nan
    rho_center_out = float(rho_np[65, 65, zo]) if voxel[65, 65, zo] == 0 else np.nan
    print()
    print("[plan_2.3V 진단] z_in/z_out 슬라이스 ρ 역산:")
    print(f"  z_in={zi}: 유체 셀 수={n_fluid_in}, 평균 ρ={mean_rho_in:.6f}")
    print(f"  z_out={zo}: 유체 셀 수={n_fluid_out}, 평균 ρ={mean_rho_out:.6f}")
    print(f"  Δρ_lbm = {delta_rho_lbm:.6f}  →  ΔP = Δρ×p_scale = {delta_P_from_rho:.6f} Pa")
    print(f"  p_scale = {p_scale:.4f}  (core.get_delta_p_pascal = {dp_sim:.6f} Pa)")
    print(f"  채널 중심 (65,65): ρ(z_in)={rho_center_in:.6f}, ρ(z_out)={rho_center_out:.6f}")

    z_cv = z_out
    cid = channel_id_ij_131()
    dx2 = DX * DX
    Q_per_ch = np.zeros(36)
    for c in range(36):
        for i in range(NX):
            for j in range(NY):
                if cid[i, j] == c:
                    Q_per_ch[c] += rho_np[i, j, z_cv] * v_np[i, j, z_cv, 2] * dx2
    Q_total = Q_per_ch.sum()
    Q_theory_per = Q_total / 36
    max_cv_pct = 0
    for c in range(36):
        if Q_theory_per > 1e-30:
            dev = abs(Q_per_ch[c] - Q_theory_per) / Q_theory_per * 100
            max_cv_pct = max(max_cv_pct, dev)
    # plan_1.91V §1.1: CV < 5%, Δρ < 3%
    pass_cv = max_cv_pct < 5.0
    delta_rho_pct = (dp_sim / (w.core.p_scale + 1e-30)) * 100
    pass_drho = delta_rho_pct < 3.0

    pass_l2 = pass_dp and pass_q and pass_clips and pass_cv and pass_drho

    # plan_1.91V §2.3: K_sim (방법 A) Darcy: K = u_superficial × μ × L / ΔP
    mu_phys = nu_phys * rho_phys
    u_superficial = u_in  # inlet = 덕트 단면 기준
    K_sim_A = u_superficial * mu_phys * L_measure / (dp_sim + 1e-30)

    print()
    print("[L2 검증 — plan_1.7V/1.91V 저유속 + NX=131 균등]")
    print(f"  채널 폭 = {CHANNEL_MM:.3f} mm, Dh = {DH_MM:.3f} mm")
    print(f"  u_channel = {u_channel:.4f} m/s, Re = {Re_ch:.1f}")
    print(f"  L_measure = {L_measure*1000:.3f} mm")
    print(f"  ΔP_theory (HP, Fanning) = {dP_theory:.6f} Pa")
    print(f"  ΔP_sim = {dp_sim:.6f} Pa")
    print(f"  오차 = {err_pct:.2f}%")
    print(f"  채널 유량 편차(최대) = {max_cv_pct:.2f}%  (기준 < 5%)")
    print(f"  Δρ_lbm = {delta_rho_pct:.2f}%  (기준 < 3%)")
    print(f"  [L2-C] K_sim(A) = {K_sim_A:.2e} m²  (Darcy: u_in×μ×L/ΔP_sim)")
    print(f"  [결과] K_sim(A) = {K_sim_A:.4e} m²")
    print(f"  판정 = {'PASS' if pass_l2 else 'FAIL'}")
    if not pass_l2:
        print(f"  [세부] ΔP:{pass_dp}, Q:{pass_q}, clips:{pass_clips}, CV:{pass_cv}, Δρ:{pass_drho}")

    # S_v (기록용)
    inner_fluid = np.sum(voxel[WALL_VOXELS:NX - WALL_VOXELS, WALL_VOXELS:NY - WALL_VOXELS, WALL_VOXELS:NZ - WALL_VOXELS] == 0)
    L_cat_m = 0.11
    perim_ch_mm = 4 * CHANNEL_MM
    total_wall_mm2 = 36 * perim_ch_mm * (L_cat_m * 1000)
    vol_mm3 = INNER_MM * INNER_MM * (L_cat_m * 1000)
    S_v_theory_si = (total_wall_mm2 / vol_mm3) * 1e3
    fluid_np = (voxel == 0)
    solid_np = (voxel == 1)
    interface_faces = 0
    for axis, shift in [(0, -1), (0, 1), (1, -1), (1, 1), (2, -1), (2, 1)]:
        interface_faces += np.sum(solid_np & np.roll(fluid_np, shift, axis=axis))
    area_voxel_m2 = interface_faces * (DX ** 2)
    vol_voxel_m3 = inner_fluid * (DX ** 3)
    S_v_voxel = area_voxel_m2 / vol_voxel_m3 if vol_voxel_m3 > 0 else 0
    dev_sv_pct = (S_v_voxel - S_v_theory_si) / (S_v_theory_si + 1e-30) * 100
    print()
    print("[S_v 편차 정량화]")
    print(f"  S_v_theory = {S_v_theory_si:.2f} 1/m, S_v_voxel = {S_v_voxel:.2f} 1/m, 편차 = {dev_sv_pct:.1f}%")

    # plan_1.91V §2.4 (선택): 출구 단면 vz 저장 — 정성 확인용
    vz_out = v_np[:, :, z_out, 2].copy()
    np.save("vz_outlet_l2_131.npy", vz_out)
    print(f"  [선택] 출구 단면 vz 저장: vz_outlet_l2_131.npy (shape {vz_out.shape})")

    return 0 if pass_l2 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
plan_1.5V §2: L2 Reference 6×6 채널 검증.
127×127×550, dx=0.2mm. 6×6 직선 채널, 완전 발달 가정 → Hagen-Poiseuille 이론 ΔP 비교.
PASS: ΔP 오차 < 5%, Q 차이 < 1%, clips=0, 채널 유량 편차 CV < 10%.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti

# plan_1.5V §2.2: 6×6 사양. 내부 23.4mm = 117 cells, 격벽 5개×5 voxels, 채널 6개
WALL_VOXELS = 5
DX_MM = 0.2
INNER_MM = 23.4  # 25.4 - 1*2
CHANNEL_MM = (INNER_MM - 5 * 1.0) / 6  # 3.067 mm
DH_MM = CHANNEL_MM
NX, NY, NZ = 127, 127, 550
DX = DX_MM * 1e-3
BUF_CELLS = 2


def make_ref6x6_voxel():
    """plan_1.5V §2.4: 6×6 Reference voxel. 외벽 5 voxel, 내부 격벽 5 voxel, 채널 fluid."""
    voxel = np.zeros((NX, NY, NZ), dtype=np.int32)
    # 외벽
    voxel[:WALL_VOXELS, :, :] = 1
    voxel[NX - WALL_VOXELS:, :, :] = 1
    voxel[:, :WALL_VOXELS, :] = 1
    voxel[:, NY - WALL_VOXELS:, :] = 1
    voxel[:, :, :WALL_VOXELS] = 1
    voxel[:, :, NZ - WALL_VOXELS:] = 1
    # 내부: 117×117. 6채널 + 5격벽. 채널폭 15,15,16,15,15,16 (합 92), 격벽 5 each.
    # i,j ∈ [5..121]. 채널 x 구간: (5,20),(25,40),(45,60),(65,80),(85,100),(105,122)
    ch_ranges_x = [(5, 20), (25, 40), (45, 60), (65, 80), (85, 100), (105, 122)]
    ch_ranges_y = [(5, 20), (25, 40), (45, 60), (65, 80), (85, 100), (105, 122)]
    for i in range(WALL_VOXELS, NX - WALL_VOXELS):
        for j in range(WALL_VOXELS, NY - WALL_VOXELS):
            in_ch_x = any(lo <= i < hi for lo, hi in ch_ranges_x)
            in_ch_y = any(lo <= j < hi for lo, hi in ch_ranges_y)
            if in_ch_x and in_ch_y:
                voxel[i, j, :] = 0
            else:
                voxel[i, j, :] = 1
    return voxel


def channel_id_ij():
    """각 (i,j)에 대해 채널 번호 0..35 (wall=-1). interior 5..121 only."""
    ch_ranges = [(5, 20), (25, 40), (45, 60), (65, 80), (85, 100), (105, 122)]
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
    import argparse
    parser = argparse.ArgumentParser(description="L2 Reference 6×6 verification")
    parser.add_argument("--plan17v", action="store_true", help="plan_1.7V: u_in 1/5 (0.0556 m/s), ΔP_theory=0.153 Pa, Δρ~2%%")
    args = parser.parse_args()
    use_plan17v = getattr(args, "plan17v", False)

    voxel = make_ref6x6_voxel()
    inner_cells = (NX - 2 * WALL_VOXELS) * (NY - 2 * WALL_VOXELS)
    fluid_cells = int((voxel == 0).sum())
    inner_fluid = np.sum(voxel[WALL_VOXELS:NX - WALL_VOXELS, WALL_VOXELS:NY - WALL_VOXELS, WALL_VOXELS:NZ - WALL_VOXELS] == 0)
    porosity = inner_fluid / (inner_cells * (NZ - 2 * WALL_VOXELS)) if (inner_cells * (NZ - 2 * WALL_VOXELS)) > 0 else 0
    cross_fluid = np.sum(voxel[WALL_VOXELS:NX - WALL_VOXELS, WALL_VOXELS:NY - WALL_VOXELS, NZ // 2] == 0)
    cross_total = (NX - 10) * (NY - 10)
    porosity_cross = cross_fluid / cross_total if cross_total > 0 else 0
    print(f"[6×6 마스크] 단면 유체/전체 = {cross_fluid}/{cross_total} = {porosity_cross:.4f}  (목표 ≈ 0.618)")

    nu_phys = 3.52e-5
    rho_phys = 0.746
    u_in = 0.0556 if use_plan17v else 0.2778
    if use_plan17v:
        print("[plan_1.7V] 저유속 모드: u_in = 0.0556 m/s, ΔP_theory = 0.153 Pa (Δρ~2% 목표)")
    area_duct_mm2 = 23.4 * 23.4
    area_channel_mm2 = 36 * (CHANNEL_MM ** 2)
    u_channel = u_in * (area_duct_mm2 / area_channel_mm2)
    Dh_m = DH_MM * 1e-3
    Re_ch = u_channel * Dh_m / nu_phys
    Le_mm = 0.05 * Re_ch * DH_MM
    print(f"  채널 폭 = {CHANNEL_MM:.3f} mm, Dh = {DH_MM:.3f} mm")
    print(f"  u_channel = {u_channel:.3f} m/s (이론 ΔP용), Re = {Re_ch:.1f}, Le = {Le_mm:.1f} mm")
    print(f"  시뮬 inlet BC: u_in = {u_in} m/s (채널 유속 가속은 시뮬 내부에서 자동)")

    from solver.taichi_lbm_core import TaichiLBMWrapper

    z_in = BUF_CELLS + 5
    z_out = NZ - 1 - BUF_CELLS - 5
    z_in = max(1, min(z_in, NZ - 2))
    z_out = max(1, min(z_out, NZ - 2))
    if z_out <= z_in:
        z_out = NZ - 2
        z_in = 1
    L_measure = (z_out - z_in) * DX  # L1과 동일: 측정면 간 거리 (덕트 전체 110 mm 아님)
    print(f"  L_measure = (z_out - z_in) × dx = {z_out - z_in} × {DX*1000} mm = {L_measure*1000:.3f} mm (HP 이론 길이)")

    # plan_v1.6.V §2.2: HP, Fanning, 정사각 단면. ΔP = 4×f_Fanning×(L_measure/Dh)×0.5×ρ×u_channel²
    f_Fanning_Re = 14.227  # 정사각 단면
    f_Fanning = f_Fanning_Re / Re_ch
    dP_theory = 4 * f_Fanning * (L_measure / Dh_m) * 0.5 * rho_phys * u_channel ** 2

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

    # plan_v1.6.V §2.5: 출구 단면(z_out)에서 36채널 유량 → CV
    rho_np = w.core.rho.to_numpy()
    v_np = w.core.v.to_numpy()
    z_cv = z_out  # 출구 단면
    cid = channel_id_ij()
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
    pass_cv = max_cv_pct < 10.0

    pass_l2 = pass_dp and pass_q and pass_clips and pass_cv

    print()
    print("[L2 검증 — Reference 6×6 채널]")
    print(f"  채널 폭 = {CHANNEL_MM:.3f} mm, Dh = {DH_MM:.3f} mm")
    print(f"  u_channel = {u_channel:.3f} m/s, Re = {Re_ch:.1f}")
    print(f"  Le = {Le_mm:.1f} mm (도메인 110mm 대비 충분)")
    print(f"  L_measure = {L_measure*1000:.3f} mm")
    print(f"  ΔP_theory (HP, Fanning) = {dP_theory:.6f} Pa")
    print(f"  ΔP_sim = {dp_sim:.6f} Pa")
    print(f"  오차 = {err_pct:.2f}%")
    print(f"  채널 유량 편차(최대) = {max_cv_pct:.2f}%")
    print(f"  판정 = {'PASS' if pass_l2 else 'FAIL'}")
    if not pass_l2:
        print(f"  [세부] ΔP:{pass_dp}, Q:{pass_q}, clips:{pass_clips}, CV:{pass_cv}")

    # plan_v1.6.V §2.6: S_v 편차 정량화 (PASS/FAIL 아님, Gyroid 보정용)
    L_cat_m = 0.11
    perim_ch_mm = 4 * CHANNEL_MM
    total_wall_mm2 = 36 * perim_ch_mm * (L_cat_m * 1000)
    vol_mm3 = 23.4 * 23.4 * (L_cat_m * 1000)
    S_v_theory_per_mm = total_wall_mm2 / vol_mm3
    S_v_theory_si = S_v_theory_per_mm * 1e3  # 1/m
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
    print("[§3 S_v 편차 정량화]")
    print(f"  S_v_theory = {S_v_theory_si:.2f} 1/m, S_v_voxel = {S_v_voxel:.2f} 1/m")
    print(f"  편차 = {dev_sv_pct:.1f}% (voxel 기준 10~30% 과대 추정 흔함)")

    return 0 if pass_l2 else 1


if __name__ == "__main__":
    sys.exit(main())

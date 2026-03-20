#!/usr/bin/env python3
"""
plan_2.4V §1: Gyroid (a=5, t=0.3) — 격자 단위 g 3개 고정값으로 주기BC 시뮬.
g_lbm = 1e-6, 5e-6, 2e-5 → 정상상태 u_superficial·ΔP·K 산출.
Guo forcing MRT 수정된 솔버 사용 (taichi_lbm_core._guo_force_source_raw + (I-S/2) 적용).
max_steps=20,000, 수렴 시 early stop 또는 max_steps.
PASS: 3개 K 편차 < 10%.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMWrapper

NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
DX = DX_MM * 1e-3
L_PHYS = NZ * DX  # 0.11 m
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS
A_MM = 5.0
T = 0.3
WALL_VOXELS = 5
# plan_2.4V §1.3: g 3개
G_VALUES = [5e-6, 2e-5, 5e-5]
MAX_STEPS = 50_000
LOG_INTERVAL = 1000


def main():
    print("[plan_2.4V] Gyroid 3-g — Guo 수정 솔버 사용 (body_force MRT with (I-S/2))")
    try:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS, u_in_phys=0.2778,
                             mode="periodic_body_force", buf_cells=2, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS, u_in_phys=0.2778,
                             mode="periodic_body_force", buf_cells=2, arch=ti.cpu)
    w.set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS, gyroid_type="network")
    A_DUCT = (NX - 2 * WALL_VOXELS) ** 2 * (DX ** 2)

    results = []
    z_mid = NZ // 2

    CONV_THRESH = 0.001  # 유량 변화율 3회 연속 < 0.1% 이면 수렴
    print(f"[Gyroid K 스케일링] max_steps={MAX_STEPS}, log_interval={LOG_INTERVAL}, 수렴기준 Q 변화율 < {CONV_THRESH*100}%")
    for g_lbm in G_VALUES:
        w.core._init_fields()
        w.core.set_body_force_z(g_lbm)
        q_history = []
        step_done = 0
        converged_at = None
        for step in range(0, MAX_STEPS, LOG_INTERVAL):
            for _ in range(LOG_INTERVAL):
                w.core.step()
            step_done = step + LOG_INTERVAL
            Q_lb = w.core.get_flux_z(z_mid)
            q_history.append(float(Q_lb))
            if len(q_history) > 3:
                q_history.pop(0)
            if len(q_history) >= 3:
                q_arr = np.array(q_history)
                q_mean = np.mean(q_arr)
                if q_mean > 1e-30:
                    change = (np.max(q_arr) - np.min(q_arr)) / q_mean
                    if change < CONV_THRESH:
                        converged_at = step_done
                        break
        dt = w.core.dt
        Q_lb = w.core.get_flux_z(z_mid)
        Q_phys = float(Q_lb) * (DX ** 3) / dt
        u_superficial = Q_phys / A_DUCT
        g_phys = g_lbm * DX / (dt ** 2)
        dP = RHO_PHYS * g_phys * L_PHYS
        K_sim = u_superficial * MU_PHYS * L_PHYS / (dP + 1e-30)
        results.append((g_lbm, u_superficial, dP, K_sim))
        # 첫 번째 스텝(g) 끝나면 수렴 스텝 확인 및 보고
        if converged_at is not None:
            print(f"  [수렴] g={g_lbm:.1e} → {converged_at} 스텝에서 수렴 (Q 변화율 3회 연속 < {CONV_THRESH*100}%)")
        else:
            print(f"  [수렴] g={g_lbm:.1e} → {step_done} 스텝 (max_steps 도달, 수렴 미달)")
        print(f"  [결과] g={g_lbm:.1e}, u_mean={u_superficial:.4f} m/s, dP={dP:.4f} Pa, K={K_sim:.4e} m²")

    K_vals = [r[3] for r in results]
    K_mean = np.mean(K_vals)
    diff_pct = [abs(k - K_mean) / (K_mean + 1e-30) * 100 for k in K_vals]
    max_diff = max(diff_pct)
    pass_scale = max_diff < 10.0
    print(f"  K 편차: max(|Ki - K_mean|)/K_mean = {max_diff:.1f}%")
    print(f"  판정: {'PASS' if pass_scale else 'FAIL'} (기준: 편차 < 10%)")

    # 완료 시 마지막 상태(g_high) VTI 저장 → results/gyroid_vti/<run_id>/
    try:
        from datetime import datetime
        from pyevtk.hl import gridToVTK
        run_id = "gyroid3g_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "gyroid_vti", run_id)
        os.makedirs(out_dir, exist_ok=True)
        dx_mm = DX_MM
        rho_np = w.core.rho.to_numpy()
        v_np = w.core.v.to_numpy()
        solid_np = w.core.solid.to_numpy()
        x = np.arange(0, NX + 1, dtype=np.float64) * dx_mm
        y = np.arange(0, NY + 1, dtype=np.float64) * dx_mm
        z = np.arange(0, NZ + 1, dtype=np.float64) * dx_mm
        path = os.path.join(out_dir, "gyroid3g_final")
        gridToVTK(path, x, y, z, cellData={
            "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
            "vz": np.ascontiguousarray(v_np[:, :, :, 2], dtype=np.float64),
            "solid": np.ascontiguousarray(solid_np.astype(np.float64), dtype=np.float64),
        })
        print(f"  [VTI] 저장: {out_dir}/gyroid3g_final.vtr (마지막 g 상태)")
    except Exception as e:
        print(f"  [VTI] 저장 생략: {e}")

    return 0 if pass_scale else 1


if __name__ == "__main__":
    sys.exit(main())

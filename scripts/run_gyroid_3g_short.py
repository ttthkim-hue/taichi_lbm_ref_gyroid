#!/usr/bin/env python3
"""
plan_2.6V §3: Gyroid 3-g 스케일링 (단축 도메인 NZ=50).
g_lbm = 5e-6, 2e-5, 5e-5 → K 산출.
PASS: K 편차 < 10%, K > 0 (3개 모두).
주기BC, Z 외벽 없음 (wall_voxels_z=0).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMWrapper

NX = NY = 131
NZ = 50  # 2 단위셀
DX_MM = 0.2
DX = DX_MM * 1e-3
A_MM = 5.0
T = 0.3
WALL_VOXELS = 5
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS

G_VALUES = [5e-6, 2e-5, 5e-5]
MAX_STEPS = 10_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001


def main():
    print("[plan_2.6V §3] Gyroid 3-g 스케일링 (NZ=50, 주기BC, wall_voxels_z=0)")
    L_phys = NZ * DX
    A_duct = (NX - 2 * WALL_VOXELS) ** 2 * DX ** 2
    z_mid = NZ // 2

    results = []
    for g_lbm in G_VALUES:
        print(f"\n--- g = {g_lbm:.1e} ---")
        try:
            w = TaichiLBMWrapper(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS,
                                 u_in_phys=0.0, mode="periodic_body_force",
                                 buf_cells=2, arch=ti.cuda)
        except Exception:
            w = TaichiLBMWrapper(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS,
                                 u_in_phys=0.0, mode="periodic_body_force",
                                 buf_cells=2, arch=ti.cpu)
        w.set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS, gyroid_type="network", wall_voxels_z=0)
        w.core.set_body_force_z(g_lbm)

        q_history = []
        converged_at = None
        step_done = 0
        for step in range(0, MAX_STEPS, LOG_INTERVAL):
            for _ in range(LOG_INTERVAL):
                w.core.step()
            step_done = step + LOG_INTERVAL
            Q_lb = float(w.core.get_flux_z(z_mid))
            q_history.append(Q_lb)
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
            print(f"  step {step_done}: Q_lb={Q_lb:.6f}")

        dt = w.core.dt
        Q_lb = float(w.core.get_flux_z(z_mid))
        Q_phys = Q_lb * DX ** 3 / dt
        u_sup = Q_phys / A_duct
        g_phys = g_lbm * DX / dt ** 2
        dP = RHO_PHYS * g_phys * L_phys
        K = u_sup * MU_PHYS * L_phys / (dP + 1e-30)

        conv_msg = f"수렴 @ {converged_at}" if converged_at else f"max {step_done}"
        print(f"  {conv_msg}, K={K:.4e} m², u_sup={u_sup:.4e} m/s, dP={dP:.4f} Pa")
        results.append((g_lbm, u_sup, dP, K))

    K_vals = [r[3] for r in results]
    K_mean = np.mean(K_vals)
    max_diff = max(abs(k - K_mean) / (K_mean + 1e-30) * 100 for k in K_vals)
    all_positive = all(k > 0 for k in K_vals)

    print(f"\n=== 3-g 스케일링 결과 ===")
    for g, u, dp, k in results:
        print(f"  g={g:.1e}: K={k:.4e}, u_sup={u:.4e}, dP={dp:.4f}")
    print(f"  K 편차: {max_diff:.2f}%")
    print(f"  K>0: {all_positive}")
    passed = max_diff < 10.0 and all_positive
    print(f"  판정: {'PASS' if passed else 'FAIL'} (기준: 편차 < 10%, K > 0)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
plan_2.6V §2: NZ 무관성 검증 — NZ=50(2 단위셀) vs NZ=550(22 단위셀).
동일 g=5e-6에서 K 차이 < 5% → PASS.
주기BC에서는 Z 방향 외벽 없음 (wall_voxels_z=0), 전체 Z에 Gyroid 배치.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMWrapper

A_MM = 5.0
T = 0.3
DX_MM = 0.2
DX = DX_MM * 1e-3
NX = NY = 131
WALL_VOXELS = 5
G_LBM = 5e-6
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS

CASES = [
    {"label": "Short (2 cells)", "nz": 50},
    {"label": "Long (22 cells)", "nz": 550},
]
MAX_STEPS = 10_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001


def run_case(nz: int, label: str):
    """Run one NZ case and return K."""
    print(f"\n--- {label}: NX={NX}, NY={NY}, NZ={nz} ---")
    L_phys = nz * DX
    A_duct = (NX - 2 * WALL_VOXELS) ** 2 * DX ** 2
    z_mid = nz // 2

    try:
        w = TaichiLBMWrapper(NX, NY, nz, DX, NU_PHYS, RHO_PHYS,
                             u_in_phys=0.0, mode="periodic_body_force",
                             buf_cells=2, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(NX, NY, nz, DX, NU_PHYS, RHO_PHYS,
                             u_in_phys=0.0, mode="periodic_body_force",
                             buf_cells=2, arch=ti.cpu)

    # Z 방향 외벽 없음 (주기BC)
    w.set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS, gyroid_type="network", wall_voxels_z=0)
    w.core.set_body_force_z(G_LBM)

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
    g_phys = G_LBM * DX / dt ** 2
    dP = RHO_PHYS * g_phys * L_phys
    K = u_sup * MU_PHYS * L_phys / (dP + 1e-30)

    conv_msg = f"수렴 @ {converged_at}" if converged_at else f"max_steps {step_done}"
    print(f"  {conv_msg}, K={K:.4e} m², u_sup={u_sup:.4e} m/s, dP={dP:.4f} Pa")
    return K


def main():
    print("[plan_2.6V §2] NZ 무관성 검증 (주기BC, wall_voxels_z=0)")

    results = {}
    for case in CASES:
        K = run_case(case["nz"], case["label"])
        results[case["nz"]] = K

    K_short = results[50]
    K_long = results[550]
    diff_pct = abs(K_short - K_long) / (abs(K_long) + 1e-30) * 100

    print(f"\n=== NZ 무관성 결과 ===")
    print(f"  K_short (NZ=50)  = {K_short:.4e} m²")
    print(f"  K_long  (NZ=550) = {K_long:.4e} m²")
    print(f"  차이 = {diff_pct:.2f}%")
    passed = diff_pct < 5.0 and K_short > 0 and K_long > 0
    print(f"  판정: {'PASS' if passed else 'FAIL'} (기준: < 5%, K > 0)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

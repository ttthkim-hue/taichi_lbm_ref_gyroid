#!/usr/bin/env python3
"""
plan_3.1V Phase 5: 반복 재현성 검증.
5개 대표점 × 3회 반복 → K CV < 0.1%.

출력:
  results/repeatability.csv         (15행)
  results/repeatability_summary.csv (5행, CV 포함)
"""
import argparse
import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DX_MM = 0.2
DX = DX_MM * 1e-3
NX = NY = 131
WALL_VOXELS = 5
G_LBM = 5e-6
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS
MAX_STEPS = 5_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001
N_REPEATS = 3

REPEAT_POINTS = [
    (3.5, 0.1),
    (5.0, 0.0),
    (5.0, 0.3),
    (8.0, -0.3),
    (10.0, -0.2),
]


def run_once(a_mm, t_val):
    import taichi as ti
    from solver.taichi_lbm_core import TaichiLBMWrapper

    nz = max(10, round(2 * a_mm / DX_MM))
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

    w.set_geometry_gyroid_kernel(a_mm, t_val, WALL_VOXELS,
                                gyroid_type="network", wall_voxels_z=0)
    w.core.set_body_force_z(G_LBM)

    solid_np = w.core.solid.to_numpy()
    interior = solid_np[WALL_VOXELS:-WALL_VOXELS, WALL_VOXELS:-WALL_VOXELS, :]
    n_fluid = int(np.sum(interior == 0))
    eps = n_fluid / (interior.size + 1e-30)

    fluid = (solid_np == 0)
    solid_bool = (solid_np == 1)
    faces = 0
    for axis in range(3):
        for shift in [-1, 1]:
            faces += np.sum(solid_bool & np.roll(fluid, shift, axis=axis))
    area = faces * DX ** 2
    vol_fluid = float(n_fluid) * DX ** 3
    S_v = area / (vol_fluid + 1e-30)

    q_history = []
    for step in range(0, MAX_STEPS, LOG_INTERVAL):
        for _ in range(LOG_INTERVAL):
            w.core.step()
        Q_lb = float(w.core.get_flux_z(z_mid))
        q_history.append(Q_lb)
        if len(q_history) > 3:
            q_history.pop(0)
        if len(q_history) >= 3:
            arr = np.array(q_history)
            mn = np.mean(arr)
            if mn > 1e-30 and (np.max(arr) - np.min(arr)) / mn < CONV_THRESH:
                break

    dt = w.core.dt
    Q_lb = float(w.core.get_flux_z(z_mid))
    Q_phys = Q_lb * DX ** 3 / dt
    u_sup = Q_phys / A_duct
    g_phys = G_LBM * DX / dt ** 2
    dP = RHO_PHYS * g_phys * L_phys
    K = u_sup * MU_PHYS * L_phys / (dP + 1e-30)
    dP_darcy = 0.2778 * MU_PHYS * 0.1 / (K + 1e-30)

    return {"K": K, "dP": dP_darcy, "S_v": S_v, "epsilon": eps}


def main():
    parser = argparse.ArgumentParser(description="Phase 5: Repeatability")
    parser.add_argument("--output", default="results/campaign_plan31v/repeatability.csv")
    parser.add_argument("--output-summary", default="results/campaign_plan31v/repeatability_summary.csv")
    args = parser.parse_args()

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)

    raw_rows = []
    summary_rows = []

    for a, t_val in REPEAT_POINTS:
        print(f"\n=== (a={a:.1f}, t={t_val:.1f}) ===")
        Ks = []
        for run in range(1, N_REPEATS + 1):
            print(f"  run {run}/{N_REPEATS} ... ", end="", flush=True)
            t0 = time.time()
            res = run_once(a, t_val)
            el = time.time() - t0
            Ks.append(res["K"])
            raw_rows.append({
                "a": a, "t": t_val, "run": run,
                "K": res["K"], "dP": res["dP"], "S_v": res["S_v"],
            })
            print(f"K={res['K']:.6e}, {el:.1f}s")

        K_arr = np.array(Ks)
        K_mean = np.mean(K_arr)
        K_std = np.std(K_arr, ddof=0)
        cv = K_std / (abs(K_mean) + 1e-30) * 100.0
        summary_rows.append({
            "a": a, "t": t_val,
            "K_mean": K_mean, "K_std": K_std, "CV_pct": cv,
        })
        verdict = "PASS" if cv < 0.1 else "FAIL"
        print(f"  → K_mean={K_mean:.6e}, CV={cv:.4f}% [{verdict}]")

    pd.DataFrame(raw_rows).to_csv(os.path.join(ROOT, args.output), index=False)
    pd.DataFrame(summary_rows).to_csv(os.path.join(ROOT, args.output_summary), index=False)

    print(f"\n[Phase 5] 재현성 검증 완료")
    print(f"  저장: {args.output} ({len(raw_rows)} rows)")
    print(f"  저장: {args.output_summary} ({len(summary_rows)} rows)")
    all_pass = all(r["CV_pct"] < 0.1 for r in summary_rows)
    print(f"  전체 PASS: {all_pass}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
plan_3.1V Phase 6: 설계 공간 경계 보강.
10×3 격자 (a=3~12, t=-0.3/0/0.3) → ~30점에서 중복 제거 후 시뮬.

출력: results/grid_supplement.csv
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

A_GRID = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
T_GRID = [-0.3, 0.0, 0.3]
EPS_BOUNDS = (0.35, 0.65)


def run_one(a_mm, t_val):
    import taichi as ti
    from solver.taichi_lbm_core import TaichiLBMWrapper

    nz = max(10, round(2 * a_mm / DX_MM))
    L_phys = nz * DX
    A_duct = (NX - 2 * WALL_VOXELS) ** 2 * DX ** 2
    z_mid = nz // 2

    t0 = time.time()
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
    S_v = faces * DX ** 2 / (float(n_fluid) * DX ** 3 + 1e-30)

    feasible = EPS_BOUNDS[0] <= eps <= EPS_BOUNDS[1]

    q_history = []
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

    elapsed = time.time() - t0

    return {
        "a": a_mm, "t": t_val, "NZ": nz,
        "epsilon": eps, "S_v": S_v, "K": K,
        "u_sup": u_sup, "dP_darcy": dP_darcy,
        "feasible": "OK" if feasible and K > 0 else "FAIL",
        "elapsed_s": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 6: Grid supplement")
    parser.add_argument("--output", default="results/campaign_plan31v/grid_supplement.csv")
    parser.add_argument("--bo-csv", default="results/campaign_plan31v/bo_results_v2.csv",
                        help="기존 BO CSV (중복 제거용)")
    args = parser.parse_args()

    grid_points = [(a, t) for a in A_GRID for t in T_GRID]

    bo_path = os.path.join(ROOT, args.bo_csv)
    if os.path.exists(bo_path):
        bo_df = pd.read_csv(bo_path)
        existing = set()
        for _, r in bo_df.iterrows():
            existing.add((round(float(r["a"]), 1), round(float(r["t"]), 1)))
        grid_points = [(a, t) for a, t in grid_points if (a, t) not in existing]

    print(f"[Phase 6] 격자 보강: {len(grid_points)} 점 (중복 제거 후)")
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)

    rows = []
    for i, (a, t_val) in enumerate(grid_points, 1):
        print(f"  [{i:02d}/{len(grid_points)}] a={a}, t={t_val} ... ", end="", flush=True)
        res = run_one(float(a), float(t_val))
        rows.append(res)
        print(f"K={res['K']:.3e}, S_v={res['S_v']:.1f}, "
              f"ε={res['epsilon']:.3f} [{res['feasible']}] {res['elapsed_s']:.1f}s")

    out_path = os.path.join(ROOT, args.output)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\n[Phase 6] 격자 보강 완료: {args.output} ({len(rows)} rows)")


if __name__ == "__main__":
    main()

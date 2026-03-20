#!/usr/bin/env python3
"""
plan_3.1V Phase 3: Forchheimer 비선형 영역 탐색.
Top-5 설계 × 5가지 g_lbm → K, β 추출.

Forchheimer: dP/L = mu*u/K + beta*rho*u^2
→ (dP/L)/u = mu/K + beta*rho*u  (선형 회귀)

출력:
  results/forchheimer.csv       (25 raw 데이터)
  results/forchheimer_fit.csv   (5 설계 × K, beta, R2)
"""
import argparse
import os
import sys
import time
import csv
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DX_MM = 0.2
DX = DX_MM * 1e-3
NX = NY = 131
WALL_VOXELS = 5
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS
MAX_STEPS = 8_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001

G_VALUES = [1e-6, 5e-6, 5e-5, 5e-4, 2e-3]


def run_single(a_mm, t_val, g_lbm):
    """단일 (a, t, g) 시뮬레이션 → u_sup, dP_L, Ma_lbm 반환."""
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
    w.core.set_body_force_z(g_lbm)

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
    g_phys = g_lbm * DX / dt ** 2
    dP = RHO_PHYS * g_phys * L_phys
    dP_L = dP / L_phys

    u_lbm_max = g_lbm * MAX_STEPS * 0.1
    vel_np = w.core.v.to_numpy()
    u_lbm_actual = np.max(np.abs(vel_np[:, :, :, 2]))
    Ma_lbm = u_lbm_actual / (1.0 / 3.0 ** 0.5)

    elapsed = time.time() - t0
    return {
        "u_sup": u_sup,
        "dP_L": dP_L,
        "Ma_lbm": Ma_lbm,
        "elapsed_s": elapsed,
        "steps": step_done,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Forchheimer analysis")
    parser.add_argument("--pareto", default="results/campaign_plan31v/pareto_front.csv")
    parser.add_argument("--top5", default="results/campaign_plan31v/top5_selected.csv")
    parser.add_argument("--output", default="results/campaign_plan31v/forchheimer.csv")
    parser.add_argument("--output-fit", default="results/campaign_plan31v/forchheimer_fit.csv")
    args = parser.parse_args()

    top5_path = os.path.join(ROOT, args.top5)
    pareto_path = os.path.join(ROOT, args.pareto)
    if os.path.exists(top5_path):
        designs = pd.read_csv(top5_path)
    elif os.path.exists(pareto_path):
        pareto = pd.read_csv(pareto_path)
        designs = pareto.head(5).copy()
        designs["design"] = [chr(65 + i) for i in range(len(designs))]
    else:
        raise FileNotFoundError("Top-5 또는 Pareto CSV를 찾을 수 없습니다.")

    os.makedirs(os.path.dirname(os.path.join(ROOT, args.output)), exist_ok=True)

    raw_rows = []
    fit_rows = []

    for _, d in designs.iterrows():
        tag = str(d.get("design", "?"))
        a = float(d["a"])
        t_val = float(d["t"])
        eps = float(d["epsilon"])
        d_pore = np.sqrt(abs(float(d["K"])) / (eps + 1e-30))

        print(f"\n=== Top-{tag}: a={a:.2f}, t={t_val:.3f} ===")
        u_list, dPL_list = [], []

        for g_lbm in G_VALUES:
            print(f"  g={g_lbm:.1e} ... ", end="", flush=True)
            res = run_single(a, t_val, g_lbm)
            u_sup = res["u_sup"]
            dP_L = res["dP_L"]
            Re_pore = abs(u_sup) * d_pore * RHO_PHYS / MU_PHYS
            print(f"u_sup={u_sup:.4e}, dP/L={dP_L:.3e}, Ma={res['Ma_lbm']:.4f}, "
                  f"Re_pore={Re_pore:.4f}, {res['elapsed_s']:.1f}s")

            raw_rows.append({
                "design": tag, "a": a, "t": t_val,
                "g_lbm": g_lbm, "u_sup": u_sup, "dP_L": dP_L,
                "Re_pore": Re_pore, "Ma_lbm": res["Ma_lbm"],
            })
            u_list.append(u_sup)
            dPL_list.append(dP_L)

        u_arr = np.array(u_list)
        dPL_arr = np.array(dPL_list)
        valid = np.abs(u_arr) > 1e-30
        if np.sum(valid) >= 2:
            y = dPL_arr[valid] / u_arr[valid]
            x = u_arr[valid]
            A_mat = np.column_stack([np.ones_like(x), RHO_PHYS * x])
            coeffs, residuals, _, _ = np.linalg.lstsq(A_mat, y, rcond=None)
            mu_over_K = coeffs[0]
            beta = coeffs[1]
            K_fit = MU_PHYS / (mu_over_K + 1e-30)
            y_pred = A_mat @ coeffs
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            R2 = 1.0 - ss_res / (ss_tot + 1e-30)
            Re_trans = MU_PHYS / (beta * RHO_PHYS * d_pore + 1e-30) if beta > 0 else float("inf")
        else:
            K_fit, beta, R2, Re_trans = float("nan"), float("nan"), float("nan"), float("nan")

        fit_rows.append({
            "design": tag, "a": a, "t": t_val,
            "K_darcy": K_fit, "beta": beta, "R2": R2,
            "Re_transition": Re_trans,
        })
        print(f"  → K_fit={K_fit:.4e}, β={beta:.4e}, R²={R2:.6f}")

    raw_df = pd.DataFrame(raw_rows)
    raw_df.to_csv(os.path.join(ROOT, args.output), index=False)
    fit_df = pd.DataFrame(fit_rows)
    fit_df.to_csv(os.path.join(ROOT, args.output_fit), index=False)

    print(f"\n[Phase 3] Forchheimer 완료")
    print(f"  저장: {args.output} ({len(raw_df)} rows)")
    print(f"  저장: {args.output_fit} ({len(fit_df)} rows)")


if __name__ == "__main__":
    main()

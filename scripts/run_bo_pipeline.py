#!/usr/bin/env python3
"""
plan_2.6V §6: Bayesian Optimization 파이프라인 (단축 도메인).

설계 변수: a ∈ [3, 8] mm, t ∈ [-0.5, 0.5]
목적함수: f1 = -S_v (최소화 → S_v 최대화), f2 = K^{-1} (최소화)
제약: ε ∈ [0.35, 0.65], 최소 벽 두께 ≥ 1.0mm

도메인: NZ = round(2*a/dx), NX=NY=131, dx=0.2mm
주기BC, g_lbm=5e-6, max_steps=5000 (수렴 시 early stop)

Usage:
  python scripts/run_bo_pipeline.py --n_init 15 --n_iter 35 --output results/bo_results.csv
"""
import sys
import os
import argparse
import csv
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np


# ── 물리 상수 ──────────────────────────────────────────────
DX_MM = 0.2
DX = DX_MM * 1e-3
NX = NY = 131
WALL_VOXELS = 5
G_LBM = 5e-6
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS
U_IN_GHSV10K = 0.2778
L_CATALYST = 0.1
MAX_STEPS = 5_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001

# ── 설계 변수 범위 ──────────────────────────────────────────
A_BOUNDS = (3.0, 8.0)   # mm
T_BOUNDS = (-0.5, 0.5)
EPS_BOUNDS = (0.35, 0.65)


def compute_Sv(solid_np, wv, dx):
    """Voxel 경계면 기반 S_v [1/m] 계산."""
    fluid = (solid_np == 0)
    solid_bool = (solid_np == 1)
    faces = 0
    for axis in range(3):
        for shift in [-1, 1]:
            faces += np.sum(solid_bool & np.roll(fluid, shift, axis=axis))
    n_fluid = np.sum(fluid[wv:-wv, wv:-wv, :])  # Z 방향 외벽 없음
    area = faces * dx ** 2
    vol_fluid = float(n_fluid) * dx ** 3
    return area / (vol_fluid + 1e-30)


def compute_epsilon(solid_np, wv):
    """Z 외벽 없는 내부 영역 공극률."""
    interior = solid_np[wv:-wv, wv:-wv, :]
    n_total = interior.size
    n_fluid = int(np.sum(interior == 0))
    return n_fluid / (n_total + 1e-30)


def evaluate(a_mm, t_val):
    """
    단일 (a, t) 케이스 평가.
    Returns: dict with plan_3.0V output columns.
    """
    import taichi as ti
    from solver.taichi_lbm_core import TaichiLBMWrapper

    nz = round(2 * a_mm / DX_MM)
    nz = max(nz, 10)
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

    w.set_geometry_gyroid_kernel(a_mm, t_val, WALL_VOXELS, gyroid_type="network", wall_voxels_z=0)
    w.core.set_body_force_z(G_LBM)

    # S_v, epsilon
    solid_np = w.core.solid.to_numpy()
    eps = compute_epsilon(solid_np, WALL_VOXELS)
    S_v = compute_Sv(solid_np, WALL_VOXELS, DX)

    # 제약 확인
    feasible = EPS_BOUNDS[0] <= eps <= EPS_BOUNDS[1]

    # LBM 수렴 실행
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

    dt = w.core.dt
    Q_lb = float(w.core.get_flux_z(z_mid))
    Q_phys = Q_lb * DX ** 3 / dt
    u_sup = Q_phys / A_duct
    g_phys = G_LBM * DX / dt ** 2
    dP = RHO_PHYS * g_phys * L_phys
    K = u_sup * MU_PHYS * L_phys / (dP + 1e-30)

    elapsed = time.time() - t0

    return {
        "a": a_mm, "t": t_val, "NZ": nz,
        "epsilon": eps, "S_v": S_v, "K": K,
        "u_sup": u_sup,
        "dP_darcy": U_IN_GHSV10K * MU_PHYS * L_CATALYST / (K + 1e-30),
        "feasible": "OK" if feasible and K > 0 else "FAIL",
        "elapsed_s": elapsed,
    }


def scalarize(S_v, K, w_Sv=0.5, w_K=0.5, S_v_ref=1000.0, K_inv_ref=1e7):
    """
    Scalarized objective for single-objective BO (minimize).
    f = -w_Sv * (S_v / S_v_ref) + w_K * (1/K) / K_inv_ref
    """
    K_inv = 1.0 / (abs(K) + 1e-30)
    return -w_Sv * (S_v / S_v_ref) + w_K * (K_inv / K_inv_ref)


def main():
    parser = argparse.ArgumentParser(description="BO Pipeline (plan_3.1V)")
    parser.add_argument("--n_init", type=int, default=15, help="초기 탐색 횟수")
    parser.add_argument("--n_iter", type=int, default=35, help="BO 반복 횟수")
    parser.add_argument("--a_min", type=float, default=None, help="a 하한 [mm]")
    parser.add_argument("--a_max", type=float, default=None, help="a 상한 [mm]")
    parser.add_argument("--output", type=str, default="results/campaign_plan31v/bo_results.csv")
    parser.add_argument("--smoke", action="store_true", help="스모크 테스트 (2회만)")
    args = parser.parse_args()

    a_lo = args.a_min if args.a_min is not None else A_BOUNDS[0]
    a_hi = args.a_max if args.a_max is not None else A_BOUNDS[1]

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    n_total = 2 if args.smoke else (args.n_init + args.n_iter)

    print(f"[BO Pipeline] Bayesian Optimization")
    print(f"  설계 변수: a ∈ [{a_lo}, {a_hi}] mm, t ∈ {T_BOUNDS}")
    print(f"  목적함수: f1 = -S_v (최소화), f2 = K^-1 (최소화)")
    print(f"  도메인: NX={NX}, NY={NY}, NZ=2*a/dx, dx={DX_MM}mm")
    print(f"  총 평가: {n_total}회 (초기 {args.n_init} + BO {args.n_iter})")
    print(f"  출력: {args.output}")
    print()

    from skopt import gp_minimize
    from skopt.space import Real

    space = [
        Real(a_lo, a_hi, name="a_mm"),
        Real(T_BOUNDS[0], T_BOUNDS[1], name="t"),
    ]

    all_results = []

    def objective(params):
        a_mm, t_val = params
        r = evaluate(a_mm, t_val)
        all_results.append(r)
        idx = len(all_results)
        feas = r["feasible"]
        print(
            f"  [{idx:03d}] a={a_mm:.2f} t={t_val:.3f} → "
            f"ε={r['epsilon']:.3f} S_v={r['S_v']:.1f} K={r['K']:.3e} "
            f"dP_darcy={r['dP_darcy']:.2f}Pa [{feas}] {r['elapsed_s']:.1f}s"
        )

        penalty = 0.0
        if r["feasible"] != "OK":
            penalty = 200.0

        score = scalarize(r["S_v"], r["K"]) + penalty
        return score

    n_init = min(args.n_init, n_total)

    result = gp_minimize(
        objective, space,
        n_calls=n_total,
        n_initial_points=n_init,
        acq_func="LCB",
        kappa=3.0,
        random_state=42,
        verbose=False,
    )

    # CSV 저장
    fieldnames = ["idx", "a", "t", "NZ", "epsilon", "S_v", "K", "u_sup", "dP_darcy", "feasible", "elapsed_s"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, r in enumerate(all_results):
            row = {"idx": i + 1}
            row.update(r)
            writer.writerow(row)

    # 결과 요약
    feasible_results = [r for r in all_results if r["feasible"] == "OK"]
    print(f"\n=== BO 결과 요약 ===")
    print(f"  총 평가: {len(all_results)}")
    print(f"  Feasible: {len(feasible_results)}")
    if feasible_results:
        best_Sv = max(feasible_results, key=lambda r: r["S_v"])
        best_K = min(feasible_results, key=lambda r: 1.0 / (r["K"] + 1e-30))
        print(f"  최고 S_v: a={best_Sv['a']:.2f} t={best_Sv['t']:.3f} → S_v={best_Sv['S_v']:.1f} 1/m")
        print(f"  최고 K:   a={best_K['a']:.2f} t={best_K['t']:.3f} → K={best_K['K']:.3e} m²")

        # Darcy ΔP 환산 (plan_2.6V §6.4)
        print(f"\n  [Darcy ΔP 환산] L_catalyst=0.1m, u_in=0.2778 m/s (GHSV 10k)")
        for r in [best_Sv, best_K]:
            print(f"    a={r['a']:.2f} t={r['t']:.3f}: K={r['K']:.3e} → ΔP={r['dP_darcy']:.2f} Pa")

    print(f"\n  결과 저장: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

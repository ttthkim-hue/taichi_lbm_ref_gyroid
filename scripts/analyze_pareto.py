#!/usr/bin/env python3
"""
plan_3.0V §2: BO 결과 Pareto 분석.

입력:
  - results/bo_results.csv
출력:
  - results/pareto_front.csv
  - results/pareto_plot.png
  - results/pareto_params.png
"""
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_pareto(costs: np.ndarray) -> np.ndarray:
    """비지배 해 마스크 반환 (모두 최소화 기준)."""
    n = costs.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        dominates = np.all(costs <= costs[i], axis=1) & np.any(costs < costs[i], axis=1)
        mask[dominates] = False
        mask[i] = True
    return mask


def topsis_rank(df, obj_cols, weights, directions):
    """TOPSIS multi-criteria decision. directions: 1=maximize, -1=minimize."""
    mat = df[obj_cols].values.astype(float).copy()
    for j, d in enumerate(directions):
        if d < 0:
            mat[:, j] = -mat[:, j]
    norms = np.sqrt((mat ** 2).sum(axis=0)) + 1e-30
    mat /= norms
    mat *= np.array(weights)
    ideal = mat.max(axis=0)
    nadir = mat.min(axis=0)
    d_plus = np.sqrt(((mat - ideal) ** 2).sum(axis=1))
    d_minus = np.sqrt(((mat - nadir) ** 2).sum(axis=1))
    score = d_minus / (d_plus + d_minus + 1e-30)
    return score


def select_top5(pareto: pd.DataFrame) -> dict:
    """Top-5 선정: A(Sv max), B(dP min), C(TOPSIS), D(eps≈0.5 Sv max), E(a≈5~6 best)."""
    p = pareto.copy()
    selected = {}
    selected["A"] = p.loc[p["S_v"].idxmax()]
    selected["B"] = p.loc[p["dP_darcy"].idxmin()]
    scores = topsis_rank(p, ["S_v", "dP_darcy"], [0.5, 0.5], [1, -1])
    selected["C"] = p.iloc[np.argmax(scores)]
    mid_eps = p[(p["epsilon"] >= 0.45) & (p["epsilon"] <= 0.55)]
    if mid_eps.empty:
        mid_eps = p.iloc[(p["epsilon"] - 0.5).abs().argsort()[:3]]
    selected["D"] = mid_eps.loc[mid_eps["S_v"].idxmax()]
    a56 = p[(p["a"] >= 4.5) & (p["a"] <= 6.5)]
    if a56.empty:
        a56 = p.iloc[(p["a"] - 5.5).abs().argsort()[:3]]
    sc56 = topsis_rank(a56, ["S_v", "dP_darcy"], [0.5, 0.5], [1, -1])
    selected["E"] = a56.iloc[np.argmax(sc56)]
    return selected


def main():
    parser = argparse.ArgumentParser(description="Analyze Pareto front from BO results")
    parser.add_argument("--input", default="results/campaign_plan31v/bo_results.csv")
    parser.add_argument("--top", type=int, default=3, help="Top-N 선정 (3 or 5)")
    parser.add_argument("--out-front", default="results/campaign_plan31v/pareto_front.csv")
    parser.add_argument("--out-plot", default="results/campaign_plan31v/pareto_plot.png")
    parser.add_argument("--out-params", default="results/campaign_plan31v/pareto_params.png")
    args = parser.parse_args()

    input_path = os.path.join(ROOT, args.input)
    out_front = os.path.join(ROOT, args.out_front)
    out_plot = os.path.join(ROOT, args.out_plot)
    out_params = os.path.join(ROOT, args.out_params)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"입력 CSV 없음: {input_path}")

    df = pd.read_csv(input_path)
    for c in ["a", "t", "NZ", "epsilon", "S_v", "K", "u_sup", "dP_darcy", "elapsed_s"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    feasible = df[df["feasible"].astype(str).str.upper() == "OK"].copy()
    feasible = feasible[(feasible["K"] > 0) & np.isfinite(feasible["S_v"]) & np.isfinite(feasible["dP_darcy"])]
    if feasible.empty:
        raise RuntimeError("Feasible 데이터가 없습니다.")

    # S_v 최대화 + dP 최소화 => [-S_v, dP] 최소화
    costs = np.column_stack([-feasible["S_v"].to_numpy(), feasible["dP_darcy"].to_numpy()])
    p_mask = is_pareto(costs)
    pareto = feasible.loc[p_mask].copy()
    pareto = pareto.sort_values(["dP_darcy", "S_v"]).reset_index(drop=True)
    pareto["sv_over_dp"] = pareto["S_v"] / (pareto["dP_darcy"] + 1e-30)

    os.makedirs(os.path.dirname(out_front), exist_ok=True)
    pareto.to_csv(out_front, index=False)

    # Figure 1: 전체 feasible + Pareto front
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    ax = axes[0]
    ax.scatter(feasible["dP_darcy"], feasible["S_v"], c="gray", alpha=0.45, s=24, label="Feasible")
    ax.scatter(pareto["dP_darcy"], pareto["S_v"], c="red", s=56, label="Pareto")
    pareto_sorted = pareto.sort_values("dP_darcy")
    ax.plot(pareto_sorted["dP_darcy"], pareto_sorted["S_v"], "r--", alpha=0.7, lw=1.2)
    ax.set_xlabel("dP_darcy [Pa] (GHSV 10k)")
    ax.set_ylabel("S_v [1/m]")
    ax.set_title("Pareto Front: S_v vs dP")
    ax.grid(alpha=0.2)
    ax.legend()

    ax = axes[1]
    sc = ax.scatter(feasible["a"], feasible["t"], c=feasible["S_v"], cmap="viridis", alpha=0.6, s=26)
    ax.scatter(pareto["a"], pareto["t"], c="red", s=64, edgecolors="black", linewidths=0.5)
    ax.set_xlabel("a [mm]")
    ax.set_ylabel("t")
    ax.set_title("Design Space (color=S_v)")
    ax.grid(alpha=0.2)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("S_v [1/m]")

    ax = axes[2]
    ax.scatter(feasible["epsilon"], feasible["K"], c="gray", alpha=0.45, s=24)
    ax.scatter(pareto["epsilon"], pareto["K"], c="red", s=56)
    ax.set_xlabel("epsilon")
    ax.set_ylabel("K [m^2]")
    ax.set_yscale("log")
    ax.set_title("Porosity vs Permeability")
    ax.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig(out_plot, dpi=180)
    plt.close(fig)

    # Figure 2: Pareto 파라미터 분포
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    ax = axes[0]
    ax.hist(pareto["a"], bins=min(10, max(3, len(pareto))), color="#4c78a8", alpha=0.8, edgecolor="black")
    ax.set_xlabel("a [mm]")
    ax.set_ylabel("count")
    ax.set_title("Pareto a distribution")
    ax.grid(alpha=0.2)

    ax = axes[1]
    ax.hist(pareto["t"], bins=min(10, max(3, len(pareto))), color="#f58518", alpha=0.8, edgecolor="black")
    ax.set_xlabel("t")
    ax.set_ylabel("count")
    ax.set_title("Pareto t distribution")
    ax.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig(out_params, dpi=180)
    plt.close(fig)

    # Top-N 선정 및 출력
    if args.top >= 5 and len(pareto) >= 3:
        top5 = select_top5(pareto)
        print("\n=== Top-5 선정 결과 ===")
        for tag, row in top5.items():
            print(f"  {tag}: a={row['a']:.2f} t={row['t']:.3f} S_v={row['S_v']:.1f} "
                  f"dP={row['dP_darcy']:.2f} ε={row['epsilon']:.3f}")
        top5_path = os.path.join(ROOT, "results", "top5_selected.csv")
        rows = []
        for tag, row in top5.items():
            r = row.to_dict()
            r["design"] = tag
            rows.append(r)
        pd.DataFrame(rows).to_csv(top5_path, index=False)
        print(f"  저장: results/top5_selected.csv")

    print(f"\n입력: {args.input}")
    print(f"Feasible 점수: {len(feasible)}")
    print(f"Pareto 점수: {len(pareto)}")
    print(f"저장: {args.out_front}")
    print(f"저장: {args.out_plot}")
    print(f"저장: {args.out_params}")


if __name__ == "__main__":
    main()

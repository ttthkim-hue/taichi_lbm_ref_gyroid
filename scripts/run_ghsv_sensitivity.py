#!/usr/bin/env python3
"""
plan_3.1V Phase 2: 다중 GHSV 압력손실 특성.
Top-5 설계에 대해 Darcy 환산으로 5가지 GHSV 조건의 dP 산출.
K는 유속 무관 → 시뮬 불필요, 직접 환산.

출력: results/ghsv_sensitivity.csv
"""
import argparse
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MU_PHYS = 3.52e-5 * 0.746
L_CATALYST = 0.1

GHSV_CONDITIONS = [
    (5000,  0.139, "저속 (저부하)"),
    (10000, 0.278, "기준 조건"),
    (20000, 0.556, "고부하"),
    (40000, 1.111, "고속 디젤"),
    (60000, 1.667, "극한 조건"),
]


def main():
    parser = argparse.ArgumentParser(description="Phase 2: GHSV sensitivity")
    parser.add_argument("--pareto", default="results/campaign_plan31v/pareto_front.csv")
    parser.add_argument("--top5", default="results/campaign_plan31v/top5_selected.csv")
    parser.add_argument("--output", default="results/campaign_plan31v/ghsv_sensitivity.csv")
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
        raise FileNotFoundError(f"Top-5 또는 Pareto CSV를 찾을 수 없습니다.")

    rows = []
    for _, d in designs.iterrows():
        tag = d.get("design", "?")
        a = float(d["a"])
        t = float(d["t"])
        K = float(d["K"])
        eps = float(d["epsilon"])
        d_pore = np.sqrt(K / eps) if eps > 0 else 1e-6

        for ghsv, u_in, label in GHSV_CONDITIONS:
            dP_darcy = u_in * MU_PHYS * L_CATALYST / (K + 1e-30)
            Re_pore = u_in * d_pore * 0.746 / MU_PHYS
            rows.append({
                "design": tag, "a": a, "t": t, "K": K,
                "GHSV": ghsv, "u_in": u_in, "dP_darcy": dP_darcy,
                "Re_pore": Re_pore,
            })

    out_path = os.path.join(ROOT, args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)

    print(f"[Phase 2] GHSV Sensitivity 완료")
    print(f"  설계 수: {len(designs)}")
    print(f"  GHSV 조건: {len(GHSV_CONDITIONS)}")
    print(f"  총 행: {len(df)}")
    print(f"  저장: {args.output}")

    for _, d in designs.iterrows():
        tag = d.get("design", "?")
        subset = df[df["design"] == tag]
        print(f"\n  Top-{tag} (a={d['a']:.2f}, t={d['t']:.3f}, K={d['K']:.3e}):")
        for _, r in subset.iterrows():
            print(f"    GHSV={int(r['GHSV']):>6} → dP={r['dP_darcy']:>8.2f} Pa, Re_pore={r['Re_pore']:.4f}")


if __name__ == "__main__":
    main()

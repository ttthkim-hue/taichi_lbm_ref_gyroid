#!/usr/bin/env python3
"""STEP 1 검증: 빈 덕트 200°C Level 1 PASS 판정."""
import pandas as pd
import math
import sys

def main():
    log_path = "/mnt/h/taichi_lbm_ref_gyroid/Results_EmptyDuct_v3/simulation_log.csv"
    try:
        df = pd.read_csv(log_path)
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    last = df.tail(200).mean(numeric_only=True)
    rho, nu, u = 0.746, 3.52e-5, 0.2778
    Dh = 126 * 0.0002
    L = 550 * 0.0002
    Re = rho * u * Dh / (nu * rho)
    f_ = 56.9 / Re
    dP_th = f_ * (L / Dh) * 0.5 * rho * u**2

    dP = last.get("dP_pascal", 0)
    Uin = last.get("Uin", last.get("u_in_sim", 0))
    imbal = last.get("mass_imbalance_pct", 999)
    err_dP = abs(dP - dP_th) / dP_th * 100 if dP_th > 0 else 0
    err_u = abs(Uin - u) / u * 100 if u > 0 else 0

    print("\n=== STEP 1: 빈 덕트 200°C ===")
    print(f"  ΔP 이론: {dP_th:.5f} Pa  시뮬: {dP:.5f} Pa  오차: {err_dP:.2f}%  {'✅' if err_dP < 1 else '❌'}")
    print(f"  Uin:     {Uin:.4f} m/s  (목표 0.2778 ±5%)  {'✅' if err_u < 5 else '❌'}")
    print(f"  질량 불균형: {imbal:.2f}%  {'✅' if imbal < 1 else '❌'}")
    pass_ = err_dP < 1 and imbal < 1 and err_u < 5
    print(f"\n  → {'✅ Level 1 PASS' if pass_ else '❌ FAIL — 중단 후 보고'}")
    sys.exit(0 if pass_ else 1)

if __name__ == "__main__":
    main()

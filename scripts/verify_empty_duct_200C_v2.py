#!/usr/bin/env python3
"""STEP 2 (V2): 빈 덕트 200°C 결과 검증 — Results_EmptyDuct_200C_v2."""
import sys

def main():
    csv_path = "/mnt/h/taichi_lbm_ref_gyroid/Results_EmptyDuct_200C_v2/simulation_log.csv"
    try:
        import pandas as pd
    except ImportError:
        print("pandas required"); sys.exit(1)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"CSV read error: {e}"); sys.exit(1)
    if len(df) < 10:
        print("Not enough rows (run longer)"); sys.exit(1)
    last = df.tail(min(200, len(df))).mean(numeric_only=True)

    rho = 0.746
    nu = 3.52e-5
    mu = nu * rho
    u = 0.2778
    Dh = 126 * 0.0002
    L = 550 * 0.0002
    Re = rho * u * Dh / mu
    f = 56.9 / Re
    dP_th = f * (L / Dh) * 0.5 * rho * u**2

    dP_sim = last.get("dP_pascal", last.get("deltaP", 0))
    u_in = last.get("u_in_sim", last.get("Uin", 0))
    u_out = last.get("u_out_sim", last.get("Uout", 0))
    rho_in = last.get("rho_in", 1.0)
    rho_out = last.get("rho_out", 1.0)
    mass_imbl = last.get("mass_imbalance_pct", 999)

    err_dP = abs(dP_sim - dP_th) / dP_th * 100 if dP_th > 0 and dP_sim > 0 else 999
    err_u = abs(u_in - u) / u * 100 if u > 0 else 999
    flux_in = rho_in * u_in
    flux_out = rho_out * u_out
    mass_imbal = abs(flux_in - flux_out) / flux_in * 100 if flux_in > 0 else mass_imbl

    print(f"\n{'='*55}")
    print("=== STEP 1: 빈 덕트 200°C 검증 (V2) ===")
    print(f"  이론 ΔP:      {dP_th:.5f} Pa  (Re={Re:.1f})")
    print(f"  시뮬 ΔP:      {dP_sim:.5f} Pa  오차={err_dP:.2f}%  {'✅' if err_dP < 1 else '❌'}")
    print(f"  Uin:          {u_in:.4f} m/s  오차={err_u:.1f}%  {'✅' if err_u < 5 else '❌'}")
    print(f"  Uout:         {u_out:.4f} m/s")
    print(f"  ρ_in/ρ_out:   {rho_in:.4f} / {rho_out:.4f}  (차이={abs(rho_in-rho_out)/rho_in*100:.1f}%)")
    print(f"  질량 불균형:  {mass_imbal:.2f}%  {'✅' if mass_imbal < 1 else '❌'}")
    pass_level1 = err_dP < 1 and mass_imbal < 1 and err_u < 5
    print(f"\n  → {'✅ Level 1 PASS — STEP 3 진행' if pass_level1 else '❌ FAIL — BC 재확인 필요'}")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()

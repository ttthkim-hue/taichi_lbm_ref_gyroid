#!/usr/bin/env python3
"""STEP 2: 빈 덕트 200°C 결과 검증 (실행지시서 V1)."""
import math
import sys

def main():
    csv_path = "/mnt/h/taichi_lbm_ref_gyroid/Results_EmptyDuct_200C/simulation_log.csv"
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
    last = df.tail(min(200, len(df))).mean()

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

    err_dP = abs(dP_sim - dP_th) / dP_th * 100 if dP_th > 0 and dP_sim > 0 else 999
    flux_in = rho_in * u_in
    flux_out = rho_out * u_out
    mass_imbal = abs(flux_in - flux_out) / flux_in * 100 if flux_in > 0 else 999

    print("=== 빈 덕트 200°C 검증 ===")
    print(f"이론 ΔP:      {dP_th:.5f} Pa  (Re={Re:.1f})")
    print(f"시뮬 ΔP:      {dP_sim:.5f} Pa  오차={err_dP:.3f}%  {'✅' if err_dP < 1 else '❌'}")
    print(f"Uin/Uout:     {u_in:.4f}/{u_out:.4f} m/s  (목표={u:.4f}, ±5%)")
    print(f"ρ_in/ρ_out:   {rho_in:.4f}/{rho_out:.4f}  (이상적=거의 동일)")
    print(f"질량 불균형:  {mass_imbal:.2f}%  {'✅ <1%' if mass_imbal < 1 else '❌'}")
    print(f"OpenLB ΔP:    0.03595 Pa (오차 0.025%)")
    pass_level2 = err_dP < 1 and mass_imbal < 1
    print(f"\n→ {'✅ Level 2 PASS' if pass_level2 else '❌ 추가 수정 필요'}")

if __name__ == "__main__":
    main()

from __future__ import annotations

"""
Taichi LBM 결과와 OpenLB 결과(JSON)를 비교해 콘솔에 요약을 출력하는 스크립트.
"""

import argparse
import json
from pathlib import Path

from validation_criteria import DEFAULT_CRITERIA


def load_json(path: str) -> dict:
    with Path(path).open() as f:
        return json.load(f)


def rel_err(a: float, b: float) -> float:
    if b == 0.0:
        return 0.0 if a == 0.0 else 1e9
    return abs(a - b) / abs(b)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--taichi", type=str, required=True, help="Taichi 결과 JSON")
    ap.add_argument("--openlb", type=str, required=True, help="OpenLB 결과 JSON")
    args = ap.parse_args()

    t = load_json(args.taichi)
    o = load_json(args.openlb)

    K_t = float(t.get("K_m2", 0.0))
    K_o = float(o.get("K_m2", 0.0))
    dP_t = float(t.get("deltaP_Pa", t.get("deltaP", 0.0)))
    dP_o = float(o.get("deltaP_Pa", o.get("deltaP", 0.0)))
    CV_t = float(t.get("CV", 0.0))
    CV_o = float(o.get("CV", 0.0))

    eK = rel_err(K_t, K_o)
    eP = rel_err(dP_t, dP_o)
    dCV = abs(CV_t - CV_o)

    crit = DEFAULT_CRITERIA
    print("=== Taichi vs OpenLB ===")
    print(f"K_taichi= {K_t:.3e}  K_openlb= {K_o:.3e}  rel_err={eK*100:.2f}%")
    print(f"ΔP_taichi= {dP_t:.4f} Pa  ΔP_openlb= {dP_o:.4f} Pa  rel_err={eP*100:.2f}%")
    print(f"CV_taichi= {CV_t:.4f}  CV_openlb= {CV_o:.4f}  |ΔCV|={dCV:.4f}")

    ok_K = eK <= crit.max_rel_err_K
    ok_P = eP <= crit.max_rel_err_deltaP
    ok_CV = dCV <= crit.max_abs_diff_CV

    print()
    print(f"K within {crit.max_rel_err_K*100:.1f}%: {'OK' if ok_K else 'NG'}")
    print(f"ΔP within {crit.max_rel_err_deltaP*100:.1f}%: {'OK' if ok_P else 'NG'}")
    print(f"|ΔCV| <= {crit.max_abs_diff_CV:.3f}: {'OK' if ok_CV else 'NG'}")


if __name__ == "__main__":
    main()


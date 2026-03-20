from __future__ import annotations

"""
Reference·Gyroid에 대한 수렴 기준 및 허용 오차 정의.
Taichi vs OpenLB 비교 시 공통으로 사용한다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationCriteria:
    # Darcy K 상대 오차 허용치 (예: 5% 이내면 OK)
    max_rel_err_K: float = 0.05
    # ΔP 상대 오차 허용치
    max_rel_err_deltaP: float = 0.05
    # CV 절대 차이 허용치
    max_abs_diff_CV: float = 0.02
    # mass conservation: 전체 밀도 변화 비율
    max_mass_drift: float = 1e-3
    # inlet/outlet flux 불균형 허용치 (상대값)
    max_flux_imbalance_rel: float = 1e-2


DEFAULT_CRITERIA = ValidationCriteria()


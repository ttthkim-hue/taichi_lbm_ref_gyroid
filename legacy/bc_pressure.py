from __future__ import annotations

"""
Pressure/velocity BC 및 mass conservation 진단을 위한 헬퍼.

Taichi 커널 내부의 구체 구현은 각 solver 모듈에서 담당하고,
여기서는 개념적 파라미터와 진단용 함수만 제공한다.
"""

from dataclasses import dataclass
from typing import Dict, Any

import numpy as np


@dataclass
class PressureRampConfig:
    delta_p_phys: float  # 목표 압력차 [Pa]
    t_ramp_phys: float   # 램프 시간 [s]

    def frac(self, t_phys: float) -> float:
        """0 ≤ t ≤ t_ramp에서 0→1로 부드럽게 증가하는 비율."""
        if t_phys >= self.t_ramp_phys:
            return 1.0
        if t_phys <= 0.0:
            return 0.0
        s = t_phys / self.t_ramp_phys
        # 간단한 3차 다항 ramp (0,0)→(1,1), 평탄한 시작/끝
        return 3 * s**2 - 2 * s**3


def mass_conservation_metrics(
    rho: np.ndarray,
    ux: np.ndarray,
    uy: np.ndarray,
    uz: np.ndarray,
    inlet_mask: np.ndarray,
    outlet_mask: np.ndarray,
    dx: float,
) -> Dict[str, Any]:
    """
    질량 보존 상태를 진단하기 위한 기본 메트릭을 계산.

    - rho_sum: 전체 도메인 밀도 합
    - inlet_flux, outlet_flux: z-direction 기준 부피 유량 [m^3/s]에 비례하는 값
    """
    assert rho.shape == ux.shape == uy.shape == uz.shape

    rho_sum = float(rho.sum())

    # inlet/outlet면에서 z-방향 속도 평균 * 단면적
    # (실제 [m^3/s] 스케일은 dx^3, dt 등을 곱해 후처리 단계에서 맞춘다)
    inlet_u = uz[inlet_mask.astype(bool)]
    outlet_u = uz[outlet_mask.astype(bool)]

    inlet_flux = float(inlet_u.mean() * inlet_u.size * dx * dx) if inlet_u.size > 0 else 0.0
    outlet_flux = float(outlet_u.mean() * outlet_u.size * dx * dx) if outlet_u.size > 0 else 0.0

    return {
        "rho_sum": rho_sum,
        "inlet_flux": inlet_flux,
        "outlet_flux": outlet_flux,
        "flux_imbalance": inlet_flux - outlet_flux,
    }


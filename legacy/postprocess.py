from __future__ import annotations

"""
Taichi LBM 결과로부터 Darcy 투과도 K, ΔP, CV 등을 계산하고
JSON/CSV로 저장하는 헬퍼.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any

import json
import numpy as np


@dataclass
class DarcyResult:
    K_m2: float
    deltaP_Pa: float
    CV: float
    converged: bool
    steps: int
    u_avg: float
    mass_drift: float | None = None
    inlet_flux: float | None = None
    outlet_flux: float | None = None


def compute_darcy_from_fields(
    u_z_phys: np.ndarray,
    p_inlet: float,
    p_outlet: float,
    rho: float,
    mu: float,
    L: float,
) -> Dict[str, Any]:
    """
    주어진 속도장/압력차로부터 Darcy K와 CV를 계산.
    u_z_phys는 [m/s] 단위의 z-성분 속도장.
    """
    fluid_mask = ~np.isnan(u_z_phys)
    u_vals = u_z_phys[fluid_mask]
    if u_vals.size == 0:
        return {
            "u_avg": 0.0,
            "K_m2": 0.0,
            "CV": 0.0,
            "deltaP_Pa": float(p_inlet - p_outlet),
        }
    u_avg = float(u_vals.mean())
    deltaP = float(p_inlet - p_outlet)
    K = 0.0
    if deltaP != 0.0:
        K = u_avg * mu * L / deltaP
    std = float(u_vals.std())
    cv = std / u_avg if abs(u_avg) > 0 else 0.0
    return {
        "u_avg": u_avg,
        "K_m2": K,
        "CV": cv,
        "deltaP_Pa": deltaP,
    }


def save_result_json(path: str | Path, result: DarcyResult) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(asdict(result), f, indent=2)


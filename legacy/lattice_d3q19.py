from __future__ import annotations

"""
D3Q19 상수 및 equilibrium 헬퍼.
Taichi 커널 내부/외부에서 모두 재사용하기 위한 순수 Python 정의.
"""

from dataclasses import dataclass
from typing import Sequence


W_VALS: list[float] = [
    1.0 / 3.0,
    *([1.0 / 18.0] * 6),
    *([1.0 / 36.0] * 12),
]

CX_VALS: list[int] = [0, 1, -1, 0, 0, 0, 0, 1, -1, -1, 1, 1, -1, -1, 1, 0, 0, 0, 0]
CY_VALS: list[int] = [0, 0, 0, 1, -1, 0, 0, 1, 1, -1, -1, 0, 0, 0, 0, 1, -1, -1, 1]
CZ_VALS: list[int] = [0, 0, 0, 0, 0, 1, -1, 0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, -1]

# bounce-back용 반대 방향 인덱스
OPP_VALS: list[int] = [0, 2, 1, 4, 3, 6, 5, 9, 10, 7, 8, 13, 14, 11, 12, 17, 18, 15, 16]


@dataclass(frozen=True)
class D3Q19:
    w: Sequence[float] = tuple(W_VALS)
    cx: Sequence[int] = tuple(CX_VALS)
    cy: Sequence[int] = tuple(CY_VALS)
    cz: Sequence[int] = tuple(CZ_VALS)
    opp: Sequence[int] = tuple(OPP_VALS)


MODEL = D3Q19()


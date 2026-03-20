from __future__ import annotations

"""
OpenLB MN .dat 파일을 읽어 Taichi LBM에서 사용할 3D 마스크/재질 배열로 변환.

MN convention (OpenLB gyroid_perm 기준):
    1: fluid
    2: solid
    3: inlet
    4: outlet

이 모듈에서는 numpy 배열로 반환하고, Taichi 쪽에서는 ti.field로 옮겨 사용한다.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np


@dataclass
class MNGeometry:
    nx: int
    ny: int
    nz: int
    mn: np.ndarray  # shape (nx, ny, nz), dtype=int32

    @property
    def solid_mask(self) -> np.ndarray:
        return (self.mn == 2).astype(np.int32)

    @property
    def fluid_mask(self) -> np.ndarray:
        return (self.mn == 1).astype(np.int32)

    @property
    def inlet_mask(self) -> np.ndarray:
        return (self.mn == 3).astype(np.int32)

    @property
    def outlet_mask(self) -> np.ndarray:
        return (self.mn == 4).astype(np.int32)


def read_mn_dat(path: str | Path) -> MNGeometry:
    p = Path(path)
    with p.open("r") as f:
        header = f.readline().strip().split()
        if len(header) != 3:
            raise ValueError(f"Invalid MN dat header in {p}: {header}")
        nx, ny, nz = map(int, header)
        n = nx * ny * nz
        vals = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            vals.append(int(line))
            if len(vals) >= n:
                break
        if len(vals) != n:
            raise ValueError(f"Expected {n} MN values, got {len(vals)} in {p}")
    arr = np.array(vals, dtype=np.int32).reshape(nx, ny, nz)
    return MNGeometry(nx=nx, ny=ny, nz=nz, mn=arr)


def inlet_outlet_porosity(mn_geom: MNGeometry) -> Tuple[float, float]:
    """
    inlet(z=0), outlet(z=nz-1) 단면에서 fluid 비율(ε)을 계산.
    """
    inlet_plane = mn_geom.mn[:, :, 0]
    outlet_plane = mn_geom.mn[:, :, mn_geom.nz - 1]
    eps_in = float((inlet_plane == 1).sum()) / inlet_plane.size
    eps_out = float((outlet_plane == 1).sum()) / outlet_plane.size
    return eps_in, eps_out


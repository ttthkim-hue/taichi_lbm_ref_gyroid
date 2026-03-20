#!/usr/bin/env python3
"""
plan_2.3V §3.1: L2-A 조건으로 수렴 후 rho, vz, solid를 VTI로 저장.
ParaView에서 Z방향 ρ 분포·XY 단면·z_in/z_out 슬라이스 확인용.

사용:
  python scripts/save_vti_l2a_diag.py [max_steps] [save_interval] [run_id]
  - max_steps: 기본 100000
  - save_interval: N 스텝마다 구간 저장. 0이면 마지막만. 기본 1000.
  - run_id: 생략 시 ref6x6_YYYYMMDD_HHMMSS 자동 생성. 동일 이름이면 덮어씀.

저장 위치 (실행마다 분리):
  - results/l2a_vti/<run_id>/ (마지막: l2a_diag.vtr, 구간: l2a_diag_step1000.vtr, ...)
  - 예: results/l2a_vti/ref6x6_20260319_091026/
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import taichi as ti

# L2-A와 동일 상수 (run_l2_ref6x6_plan17v와 일치)
WALL_VOXELS = 5
NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
DX = DX_MM * 1e-3
BUF_CELLS = 2


def make_ref6x6_voxel_131():
    ch_ranges = [(5, 21), (26, 42), (47, 63), (68, 84), (89, 105), (110, 126)]
    voxel = np.zeros((NX, NY, NZ), dtype=np.int32)
    voxel[:WALL_VOXELS, :, :] = 1
    voxel[NX - WALL_VOXELS:, :, :] = 1
    voxel[:, :WALL_VOXELS, :] = 1
    voxel[:, NY - WALL_VOXELS:, :] = 1
    voxel[:, :, :WALL_VOXELS] = 1
    voxel[:, :, NZ - WALL_VOXELS:] = 1
    for i in range(WALL_VOXELS, NX - WALL_VOXELS):
        for j in range(WALL_VOXELS, NY - WALL_VOXELS):
            in_ch = any(lo <= i < hi for lo, hi in ch_ranges) and any(lo <= j < hi for lo, hi in ch_ranges)
            voxel[i, j, :] = 0 if in_ch else 1
    return voxel


VTI_BASE = "l2a_diag"
# OUT_DIR = results/l2a_vti/<run_id> (main에서 run_id로 생성)
# 스텝 간격으로 저장 (0이면 마지막에만 저장). L2-A 수렴 ~7k이므로 1000 단위로 저장.
SAVE_INTERVAL = 1_000  # 1k, 2k, ..., 7k(수렴), ... → 수렴 전후 시각화 가능


def _write_vti(out_dir: str, base: str, step: int, rho_np, v_np, solid_np, dx_mm: float) -> str:
    from pyevtk.hl import gridToVTK
    x = np.arange(0, NX + 1, dtype=np.float64) * dx_mm
    y = np.arange(0, NY + 1, dtype=np.float64) * dx_mm
    z = np.arange(0, NZ + 1, dtype=np.float64) * dx_mm
    path = os.path.join(out_dir, f"{base}_step{step}")
    gridToVTK(
        path,
        x, y, z,
        cellData={
            "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
            "vz": np.ascontiguousarray(v_np[:, :, :, 2], dtype=np.float64),
            "solid": np.ascontiguousarray(solid_np.astype(np.float64), dtype=np.float64),
        },
    )
    return path + ".vti"


def main():
    # 인자: max_steps [save_interval] [run_id]
    max_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    save_interval = int(sys.argv[2]) if len(sys.argv) > 2 else SAVE_INTERVAL
    if len(sys.argv) > 3:
        run_id = sys.argv[3].strip()
    else:
        from datetime import datetime
        run_id = "ref6x6_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "l2a_vti", run_id)
    os.makedirs(out_dir, exist_ok=True)
    print(f"[save_vti_l2a_diag] run_id={run_id} → {out_dir}")

    voxel = make_ref6x6_voxel_131()
    nu_phys = 3.52e-5
    rho_phys = 0.746
    L_measure = 0.107
    Dh_m = 0.0032
    u_channel_HP = 0.153 * (Dh_m ** 2) / (2.0 * 14.227 * nu_phys * L_measure * rho_phys)
    area_channel_mm2 = 36 * (3.2 ** 2)
    area_duct_mm2 = 24.2 ** 2
    u_in = u_channel_HP * (area_channel_mm2 / area_duct_mm2)

    try:
        from pyevtk.hl import gridToVTK
    except ImportError:
        print("pyevtk 없음. pip install pyevtk 후 재실행.")
        return 1

    from solver.taichi_lbm_core import TaichiLBMWrapper
    try:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=BUF_CELLS, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(NX, NY, NZ, DX, nu_phys, rho_phys, u_in_phys=u_in, buf_cells=BUF_CELLS, arch=ti.cpu)
    w.set_geometry_from_voxel(voxel)

    dx_mm = DX * 1000.0
    print(f"[save_vti_l2a_diag] Running {max_steps} steps, save_interval={save_interval or 'last only'}...")
    saved = []

    for step in range(1, max_steps + 1):
        w.core.step()
        if save_interval > 0 and step % save_interval == 0:
            rho_np = w.core.rho.to_numpy()
            v_np = w.core.v.to_numpy()
            solid_np = w.core.solid.to_numpy()
            p = _write_vti(out_dir, VTI_BASE, step, rho_np, v_np, solid_np, dx_mm)
            saved.append(p)
            print(f"[save_vti_l2a_diag] Saved {p} (step {step})")

    rho_np = w.core.rho.to_numpy()
    v_np = w.core.v.to_numpy()
    solid_np = w.core.solid.to_numpy()
    path_last = os.path.join(out_dir, VTI_BASE)
    gridToVTK(
        path_last,
        np.arange(0, NX + 1, dtype=np.float64) * dx_mm,
        np.arange(0, NY + 1, dtype=np.float64) * dx_mm,
        np.arange(0, NZ + 1, dtype=np.float64) * dx_mm,
        cellData={
            "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
            "vz": np.ascontiguousarray(v_np[:, :, :, 2], dtype=np.float64),
            "solid": np.ascontiguousarray(solid_np.astype(np.float64), dtype=np.float64),
        },
    )
    print(f"[save_vti_l2a_diag] Saved {path_last}.vti (rho, vz, solid) [final step {max_steps}]")
    if saved:
        print(f"[save_vti_l2a_diag] Interval saves: {saved}")
    print(f"[save_vti_l2a_diag] 출력 디렉터리: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Gyroid 진단용 VTI/VTR 저장.
주기BC + 체적력 g=5e-6, 5000스텝 실행 후 유동장 저장.
plan_2.5V §2.1
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMWrapper

# ── 설정 ──
NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
DX = DX_MM * 1e-3
NU_PHYS = 3.52e-5
RHO_PHYS = 0.746
TAU = 0.595
A_MM, T_PARAM = 5.0, 0.3
WALL_VOXELS = 5
G_LBM = 5e-6
MAX_STEPS = 5000
SAVE_INTERVAL = 1000  # 매 1000스텝 VTR 저장

# 결과 디렉터리 (프로젝트 루트 기준)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def main():
    ti.init(arch=ti.cuda)

    try:
        wrapper = TaichiLBMWrapper(
            NX, NY, NZ, DX, NU_PHYS, RHO_PHYS,
            u_in_phys=0.0,
            tau=TAU,
            mode="periodic_body_force",
            buf_cells=2,
            arch=ti.cuda,
        )
    except Exception:
        wrapper = TaichiLBMWrapper(
            NX, NY, NZ, DX, NU_PHYS, RHO_PHYS,
            u_in_phys=0.0,
            tau=TAU,
            mode="periodic_body_force",
            buf_cells=2,
            arch=ti.cpu,
        )
    wrapper.set_geometry_gyroid_kernel(A_MM, T_PARAM, WALL_VOXELS, gyroid_type="network")
    wrapper.core.set_body_force_z(G_LBM)

    from pyevtk.hl import gridToVTK

    def save_vtr(step_label):
        """현재 유동장을 VTR로 저장"""
        rho_np = wrapper.core.rho.to_numpy()
        vel_np = wrapper.core.v.to_numpy()  # (NX, NY, NZ, 3)
        solid_np = wrapper.core.solid.to_numpy()

        vz = vel_np[:, :, :, 2]

        x = np.arange(0, NX + 1, dtype=np.float64) * DX_MM
        y = np.arange(0, NY + 1, dtype=np.float64) * DX_MM
        z = np.arange(0, NZ + 1, dtype=np.float64) * DX_MM

        path = os.path.join(RESULTS_DIR, f"gyroid_diag_step{step_label}")
        gridToVTK(
            path, x, y, z,
            cellData={
                "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
                "vz": np.ascontiguousarray(vz, dtype=np.float64),
                "solid": np.ascontiguousarray(solid_np.astype(np.float64)),
            },
        )
        print(f"  VTR 저장: {path}.vtr")

    # 초기 상태 저장
    save_vtr("0000")

    z_mid = NZ // 2
    for step in range(1, MAX_STEPS + 1):
        wrapper.core.step()

        if step % SAVE_INTERVAL == 0:
            flux = wrapper.core.get_flux_z(z_mid)
            rho_np = wrapper.core.rho.to_numpy()
            solid_np = wrapper.core.solid.to_numpy()
            fluid_mask = solid_np == 0
            rho_mean = np.mean(rho_np[fluid_mask]) if np.any(fluid_mask) else 0.0

            print(f"  step {step}: flux_z(mid)={flux:.6f}, rho_mean={rho_mean:.6f}")
            save_vtr(f"{step:04d}")

    save_vtr("final")
    print("\n[완료] VTR 파일 저장 위치: results/gyroid_diag_*.vtr")


if __name__ == "__main__":
    main()

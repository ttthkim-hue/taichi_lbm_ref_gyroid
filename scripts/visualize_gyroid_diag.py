#!/usr/bin/env python3
"""
Gyroid 마스크 + 유동장 pyvista 시각화.
VTR 파일이 있으면 VTR에서 로드, 없으면 마스크만 생성하여 시각화.
plan_2.5V §2.5
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pyvista as pv
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMCore

pv.OFF_SCREEN = True

NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def main():
    ti.init(arch=ti.cuda)

    core = TaichiLBMCore(
        NX, NY, NZ,
        DX_MM * 1e-3,
        3.52e-5, 0.746,
        u_in_phys=0.2778,
        tau=0.595,
    )
    core.set_geometry_gyroid_kernel(5.0, 0.3, 5, gyroid_type="network")
    solid = core.solid.to_numpy()

    # UniformGrid: dimensions = (nx+1, ny+1, nz+1) points → NX*NY*NZ cells
    grid = pv.ImageData(
        dimensions=(NX + 1, NY + 1, NZ + 1),
        spacing=(DX_MM, DX_MM, DX_MM),
    )
    grid.cell_data["solid"] = solid.flatten(order="F")

    # ── 1. XY 단면 (z=275) — solid 패턴 ──
    slice_xy = grid.slice(normal="z", origin=(0, 0, 275 * DX_MM))
    pl = pv.Plotter(off_screen=True)
    pl.add_mesh(slice_xy, scalars="solid", cmap="gray", show_edges=False)
    pl.add_title("solid XY (z=275)")
    pl.camera_position = "xy"
    pl.screenshot(os.path.join(RESULTS_DIR, "gyroid_solid_xy_z275.png"), window_size=[1200, 1200])
    pl.close()

    # ── 2. XZ 단면 (y=65) — Z 관통 확인 ──
    slice_xz = grid.slice(normal="y", origin=(0, 65 * DX_MM, 0))
    pl = pv.Plotter(off_screen=True)
    pl.add_mesh(slice_xz, scalars="solid", cmap="gray", show_edges=False)
    pl.add_title("solid XZ (y=65) — Z 관통 확인")
    pl.camera_position = "xz"
    pl.screenshot(os.path.join(RESULTS_DIR, "gyroid_solid_xz_y65.png"), window_size=[1600, 400])
    pl.close()

    # ── 3. 3D isosurface (solid 경계면) ──
    fluid = grid.threshold(value=0.5, scalars="solid", invert=True)
    pl = pv.Plotter(off_screen=True)
    pl.add_mesh(fluid, color="steelblue", opacity=0.3)
    pl.add_title("Gyroid fluid region (3D)")
    pl.camera_position = "iso"
    pl.screenshot(os.path.join(RESULTS_DIR, "gyroid_3d_fluid.png"), window_size=[1200, 1200])
    pl.close()

    print("저장 완료:")
    print("  results/gyroid_solid_xy_z275.png")
    print("  results/gyroid_solid_xz_y65.png")
    print("  results/gyroid_3d_fluid.png")

    # ── VTR이 있으면 vz XY 단면 추가 ──
    vtr_path = os.path.join(RESULTS_DIR, "gyroid_diag_step5000.vtr")
    if os.path.exists(vtr_path):
        mesh = pv.read(vtr_path)
        sl = mesh.slice(normal="z", origin=(0, 0, 275 * DX_MM))
        pl = pv.Plotter(off_screen=True)
        pl.add_mesh(sl, scalars="vz", cmap="coolwarm", show_edges=False)
        pl.add_title("vz XY (z=275, step 5000)")
        pl.camera_position = "xy"
        pl.screenshot(os.path.join(RESULTS_DIR, "gyroid_vz_xy_z275.png"), window_size=[1200, 1200])
        pl.close()
        print("  results/gyroid_vz_xy_z275.png")


if __name__ == "__main__":
    main()

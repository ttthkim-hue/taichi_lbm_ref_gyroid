#!/usr/bin/env python3
"""
Gyroid 마스크 생성 후 Z 관통 경로 수 확인.
시뮬 불필요 — 마스크만 생성하여 분석.
plan_2.5V §1.1
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMCore

ti.init(arch=ti.cuda)

NX, NY, NZ = 131, 131, 550
DX = 0.2e-3
NU_PHYS = 3.52e-5
RHO_PHYS = 0.746
A_MM, T = 5.0, 0.3
WALL = 5

core = TaichiLBMCore(NX, NY, NZ, DX, NU_PHYS, RHO_PHYS, u_in_phys=0.2778, tau=0.595)
core.set_geometry_gyroid_kernel(A_MM, T, WALL, gyroid_type="network")
solid = core.solid.to_numpy()  # (NX, NY, NZ), 0=fluid, 1=solid

# ── 진단 1: Z 관통 경로 ──
fluid_all_z = np.all(solid == 0, axis=2)
n_through = int(np.sum(fluid_all_z))
print(f"[진단1] Z 관통 유체 셀 수: {n_through}")
print(f"  → {'❌ Z 방향 막힘 (Sheet 분리)' if n_through == 0 else '✅ Z 관통 경로 있음'}")

# ── 진단 2: 슬라이스별 유체 비율 ──
print("\n[진단2] 슬라이스별 유체 비율:")
for z in [0, 5, 50, 100, 275, 450, 500, 545, 549]:
    ratio = np.mean(solid[:, :, z] == 0)
    print(f"  z={z:3d}: fluid={ratio:.4f}")

# ── 진단 3: 전체 공극률 ──
eps = np.mean(solid == 0)
print(f"\n[진단3] 전체 공극률 ε = {eps:.4f}")

# ── 진단 4: XY 중앙 단면 solid 패턴 ──
mid_z = NZ // 2
mid_y = NY // 2
print(f"\n[진단4] solid 패턴 (z={mid_z}):")
print(f"  유체 셀 수: {np.sum(solid[:, :, mid_z] == 0)} / {NX*NY}")

print(f"\n[진단4] solid 패턴 XZ (y={mid_y}):")
print(f"  유체 셀 수: {np.sum(solid[:, mid_y, :] == 0)} / {NX*NZ}")

# ── 진단 5: 외벽 내부만 Z 관통 확인 ──
interior = solid[WALL:-WALL, WALL:-WALL, :]  # 외벽 제외
fluid_interior_z = np.all(interior == 0, axis=2)
n_interior = int(np.sum(fluid_interior_z))
print(f"\n[진단5] 외벽 제외 내부 Z 관통: {n_interior}")

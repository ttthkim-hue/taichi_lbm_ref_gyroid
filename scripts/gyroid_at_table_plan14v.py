#!/usr/bin/env python3
"""
plan_1.4V §3: Gyroid 커널 (a, t) 조합에 대한 ε(공극률), min_wall_voxels 테이블.
BO 설계 변수 범위 재조정용.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import taichi as ti

# 격자는 Coarse 크기로 (64×64×275), 빠른 검증용
NX, NY, NZ = 64, 64, 275
DX_MM = 0.4
WALL_VOXELS = 5

def compute_epsilon_and_minwall(solid_np: np.ndarray) -> tuple:
    """내부(덕트 벽 제외)에서 ε = 유체비율, min_wall = 최소 고체 연속 길이."""
    w = WALL_VOXELS
    interior = solid_np[w:NX-w, w:NY-w, w:NZ-w]
    n_total = interior.size
    n_solid = int(interior.sum())
    n_fluid = n_total - n_solid
    eps = n_fluid / n_total if n_total > 0 else 0.0

    def min_run_1d(arr: np.ndarray) -> int:
        run = 0
        min_run = n_total + 1
        for x in arr.ravel():
            if x == 1:
                run += 1
            else:
                if run > 0:
                    min_run = min(min_run, run)
                run = 0
        if run > 0:
            min_run = min(min_run, run)
        return min_run if min_run <= n_total else 0

    min_wall = NX + 1
    for i in range(w, NX - w, max(1, (NX - 2 * w) // 5)):
        for j in range(w, NY - w, max(1, (NY - 2 * w) // 5)):
            r = min_run_1d(solid_np[i, j, w:NZ-w])
            if r > 0:
                min_wall = min(min_wall, r)
    for i in range(w, NX - w, max(1, (NX - 2 * w) // 5)):
        for k in range(w, NZ - w, max(1, (NZ - 2 * w) // 5)):
            r = min_run_1d(solid_np[i, w:NY-w, k])
            if r > 0:
                min_wall = min(min_wall, r)
    for j in range(w, NY - w, max(1, (NY - 2 * w) // 5)):
        for k in range(w, NZ - w, max(1, (NZ - 2 * w) // 5)):
            r = min_run_1d(solid_np[w:NX-w, j, k])
            if r > 0:
                min_wall = min(min_wall, r)
    if min_wall > NX:
        min_wall = 0
    return eps, min_wall

def main():
    dx_m = DX_MM * 1e-3
    from solver.taichi_lbm_core import TaichiLBMCore

    core = TaichiLBMCore(NX, NY, NZ, dx_m, 3.52e-5, 0.746, 0.2778, 0.595, arch=ti.cpu)
    core._static_done = True  # geometry만 설정, 필드 초기화는 set_geometry에서

    cases = [
        (5.0, 0.0),
        (5.0, 0.1),
        (5.0, 0.3),
        (5.0, 0.5),
        (3.0, 0.3),
        (8.0, 0.1),
    ]

    print("plan_1.4V §3: (a, t) → (ε, min_wall_voxels)")
    print("Grid:", NX, "×", NY, "×", NZ, "dx=", DX_MM, "mm")
    print("-" * 50)
    rows = []
    for a_mm, t in cases:
        core.set_geometry_gyroid_kernel(a_mm, t, wall_voxels=WALL_VOXELS)
        solid_np = core.solid.to_numpy()
        eps, min_wall = compute_epsilon_and_minwall(solid_np)
        rows.append((a_mm, t, eps, min_wall))
        in_range = "✓" if 0.35 <= eps <= 0.65 else ""
        wall_ok = "✓" if min_wall >= 3 else "⚠"
        print(f"  a={a_mm:.1f}  t={t:.1f}  →  ε={eps:.3f}  min_wall={min_wall}  ε∈[0.35,0.65] {in_range}  wall≥3 {wall_ok}")
    print("-" * 50)
    print("(a,t) → (ε, min_wall_voxels) 매핑 완료. BO t 범위 검토 시 사용.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

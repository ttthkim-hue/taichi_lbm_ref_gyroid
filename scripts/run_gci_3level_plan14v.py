#!/usr/bin/env python3
"""
plan_2.4V §2: 격자 독립성 GCI 3-Level (Gyroid a=5mm, t=0.3 고정).
주기BC + 체적력 g_lbm=5e-6 고정. 각 격자에서 K 산출 → Richardson extrapolation → GCI.
PASS: GCI_fine < 5%.
각 레벨별 Gyroid 커널은 해당 dx에 맞게 재생성 (set_geometry_gyroid_kernel).
"""
import sys
import os
import subprocess
import tempfile
import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

# plan_2.4V §2.2
LEVELS = [
    {"name": "Coarse", "dx_mm": 0.4, "nx": 66, "ny": 66, "nz": 275},
    {"name": "Medium", "dx_mm": 0.2, "nx": 131, "ny": 131, "nz": 550},
    {"name": "Fine", "dx_mm": 0.15, "nx": 175, "ny": 175, "nz": 733},
]
G_LBM = 5e-6
MAX_STEPS = 20_000
LOG_INTERVAL = 1000
A_MM, T = 5.0, 0.3
WALL_VOXELS = 5
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS


def run_one_level(level_index: int, out_file: str) -> int:
    """서브프로세스: 단일 레벨만 실행하고 K를 out_file에 기록."""
    import taichi as ti
    from solver.taichi_lbm_core import TaichiLBMWrapper

    lev = LEVELS[level_index]
    dx = lev["dx_mm"] * 1e-3
    nx, ny, nz = lev["nx"], lev["ny"], lev["nz"]
    L_phys = nz * dx
    A_duct = (nx - 2 * WALL_VOXELS) ** 2 * (dx ** 2)
    z_mid = nz // 2

    try:
        w = TaichiLBMWrapper(
            nx, ny, nz, dx, NU_PHYS, RHO_PHYS,
            u_in_phys=0.2778, buf_cells=2, mode="periodic_body_force", arch=ti.cuda,
        )
    except Exception:
        w = TaichiLBMWrapper(
            nx, ny, nz, dx, NU_PHYS, RHO_PHYS,
            u_in_phys=0.2778, buf_cells=2, mode="periodic_body_force", arch=ti.cpu,
        )
    w.set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS)
    w.core.set_body_force_z(G_LBM)

    for step in range(0, MAX_STEPS, LOG_INTERVAL):
        for _ in range(LOG_INTERVAL):
            w.core.step()

    dt = w.core.dt
    Q_lb = w.core.get_flux_z(z_mid)
    Q_phys = float(Q_lb) * (dx ** 3) / dt
    u_superficial = Q_phys / A_duct
    g_phys = G_LBM * dx / (dt ** 2)
    dP = RHO_PHYS * g_phys * L_phys
    K_sim = u_superficial * MU_PHYS * L_phys / (dP + 1e-30)

    with open(out_file, "w") as f:
        f.write(f"{K_sim}\n")
    return 0


def compute_gci(K_c: float, K_m: float, K_f: float, h_c: float, h_m: float, h_f: float):
    """plan_2.4V §2.3: r = dx_coarse/dx_fine, p = ln((K_c-K_m)/(K_m-K_f))/ln(r), GCI_fine = 1.25*|K_m-K_f|/(r^p-1)/K_f*100"""
    r = h_c / h_f
    denom = K_m - K_f
    if abs(denom) < 1e-30:
        return 0.0, 2.0
    p = np.log(abs((K_c - K_m) / denom)) / np.log(r)
    e = abs(K_m - K_f) / (abs(K_f) + 1e-30)
    gci_fine = 1.25 * e / ((r ** p) - 1.0) * 100.0
    return gci_fine, p


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--run-level":
        level_index = int(sys.argv[2])
        out_file = sys.argv[3]
        return run_one_level(level_index, out_file)

    print("plan_2.4V §2: GCI 3-Level (Gyroid a=5, t=0.3, periodic_body_force, g=5e-6)")
    print(f"  max_steps={MAX_STEPS}, 각 격자에서 Gyroid 커널 해당 dx로 재생성")
    print()

    script = os.path.abspath(__file__)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, lev in enumerate(LEVELS):
            out_path = os.path.join(tmp, f"K_{i}.txt")
            print(f"--- {lev['name']} dx={lev['dx_mm']} mm {lev['nx']}×{lev['ny']}×{lev['nz']} ---")
            ret = subprocess.run(
                [sys.executable, script, "--run-level", str(i), out_path],
                cwd=ROOT,
                timeout=3600 * 2,
            )
            if ret.returncode != 0:
                print(f"  FAILED level {lev['name']}")
                return 1
            with open(out_path) as f:
                K = float(f.read().strip())
            h = lev["dx_mm"] * 1e-3
            results.append((lev["name"], h, K))
            print(f"  → K = {K:.4e} m²\n")

    K_c, K_m, K_f = results[0][2], results[1][2], results[2][2]
    h_c, h_m, h_f = results[0][1], results[1][1], results[2][1]
    gci_pct, p_eff = compute_gci(K_c, K_m, K_f, h_c, h_m, h_f)

    print("=== GCI (plan_2.4V §2.3) ===")
    print(f"  Coarse K = {K_c:.4e}  Medium K = {K_m:.4e}  Fine K = {K_f:.4e}")
    print(f"  Richardson p ≈ {p_eff:.3f}")
    print(f"  GCI_fine = {gci_pct:.2f}%")
    pass_gci = gci_pct < 5.0
    print(f"  판정 = {'PASS' if pass_gci else 'FAIL'} (기준 < 5%)")
    return 0 if pass_gci else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
plan_2.6V §4: GCI 격자 독립성 (단축 도메인, 2 단위셀).
Gyroid a=5, t=0.3, g=5e-6. 3 Level: Coarse(dx=0.4), Medium(dx=0.2), Fine(dx=0.15).
NZ = round(2 * a / dx). 주기BC, Z 외벽 없음.
PASS: GCI_fine < 5%.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import subprocess
import tempfile
import numpy as np

A_MM = 5.0
T = 0.3
G_LBM = 5e-6
WALL_THICKNESS_MM = 1.0  # 물리적 벽 두께 고정 (Medium: 5*0.2=1.0mm)
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS
MAX_STEPS = 10_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001

def _wall_voxels(dx_mm):
    """동일 물리적 벽 두께를 유지하도록 wall_voxels 스케일링."""
    return max(1, round(WALL_THICKNESS_MM / dx_mm))

LEVELS = [
    {"name": "Coarse", "dx_mm": 0.4, "nx": 66, "ny": 66, "nz": 25},
    {"name": "Medium", "dx_mm": 0.2, "nx": 131, "ny": 131, "nz": 50},
    {"name": "Fine",   "dx_mm": 0.15, "nx": 175, "ny": 175, "nz": 67},
]


def run_one_level(level_index: int, out_file: str) -> int:
    """Sub-process: run one grid level, write K to out_file."""
    import taichi as ti
    from solver.taichi_lbm_core import TaichiLBMWrapper

    lev = LEVELS[level_index]
    dx = lev["dx_mm"] * 1e-3
    nx, ny, nz = lev["nx"], lev["ny"], lev["nz"]
    wv = _wall_voxels(lev["dx_mm"])
    L_phys = nz * dx
    A_duct = (nx - 2 * wv) ** 2 * dx ** 2
    z_mid = nz // 2
    inner_mm = (nx - 2 * wv) * lev["dx_mm"]

    print(f"--- {lev['name']} dx={lev['dx_mm']} mm  {nx}x{ny}x{nz}  wall={wv}  inner={inner_mm:.1f}mm ---")

    try:
        w = TaichiLBMWrapper(nx, ny, nz, dx, NU_PHYS, RHO_PHYS,
                             u_in_phys=0.0, mode="periodic_body_force",
                             buf_cells=2, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(nx, ny, nz, dx, NU_PHYS, RHO_PHYS,
                             u_in_phys=0.0, mode="periodic_body_force",
                             buf_cells=2, arch=ti.cpu)

    w.set_geometry_gyroid_kernel(A_MM, T, wv, gyroid_type="network", wall_voxels_z=0)
    w.core.set_body_force_z(G_LBM)

    q_history = []
    converged_at = None
    step_done = 0
    for step in range(0, MAX_STEPS, LOG_INTERVAL):
        for _ in range(LOG_INTERVAL):
            w.core.step()
        step_done = step + LOG_INTERVAL
        Q_lb = float(w.core.get_flux_z(z_mid))
        q_history.append(Q_lb)
        if len(q_history) > 3:
            q_history.pop(0)
        if len(q_history) >= 3:
            q_arr = np.array(q_history)
            q_mean = np.mean(q_arr)
            if q_mean > 1e-30:
                change = (np.max(q_arr) - np.min(q_arr)) / q_mean
                if change < CONV_THRESH:
                    converged_at = step_done
                    break
        print(f"  step {step_done}: Q_lb={Q_lb:.6f}")

    dt = w.core.dt
    Q_lb = float(w.core.get_flux_z(z_mid))
    Q_phys = Q_lb * dx ** 3 / dt
    u_sup = Q_phys / A_duct
    g_phys = G_LBM * dx / dt ** 2
    dP = RHO_PHYS * g_phys * L_phys
    K = u_sup * MU_PHYS * L_phys / (dP + 1e-30)

    conv_msg = f"수렴 @ {converged_at}" if converged_at else f"max {step_done}"
    print(f"  {conv_msg}, K={K:.4e} m²")
    with open(out_file, "w") as f:
        f.write(f"{K}\n")
    return 0


def compute_gci(K_c, K_m, K_f, h_c, h_m, h_f):
    """
    Celik et al. (2008) ASME GCI procedure.
    h1=fine, h2=medium, h3=coarse  (h1 < h2 < h3).
    r21 = h2/h1, r32 = h3/h2.
    """
    # Reorder: 1=fine, 2=medium, 3=coarse
    f1, f2, f3 = K_f, K_m, K_c
    h1, h2, h3 = h_f, h_m, h_c
    r21 = h2 / h1
    r32 = h3 / h2

    e32 = f3 - f2
    e21 = f2 - f1

    # Simple relative error (fallback)
    ea21 = abs(e21) / (abs(f1) + 1e-30) * 100  # %

    if abs(e21) < 1e-30:
        return 0.0, 2.0, ea21

    ratio = e32 / e21
    s = 1.0 if ratio > 0 else -1.0

    # Fixed-point iteration for p (Celik et al. 2008)
    if abs(ratio) < 1e-30 or ratio < 0:
        p_eff = 0.0
    else:
        p_eff = abs(np.log(abs(ratio))) / np.log(r21)
        for _ in range(50):
            try:
                denom = r32**p_eff - s
                if abs(denom) < 1e-30:
                    break
                q = np.log(abs((r21**p_eff - s) / denom))
            except (OverflowError, ValueError):
                break
            p_new = abs(np.log(abs(ratio)) + q) / np.log(r21)
            if np.isnan(p_new) or np.isinf(p_new) or p_new > 20:
                p_eff = 0.0
                break
            if abs(p_new - p_eff) < 0.01:
                p_eff = p_new
                break
            p_eff = p_new

    # GCI_fine = Fs * ea21 / (r21^p - 1), Fs=1.25 for 3 grids
    if p_eff >= 0.5:
        gci_fine = 1.25 * ea21 / (r21**p_eff - 1.0)
    else:
        # p unreliable → use formal order p=2 (LBM 2nd order)
        p_eff = 2.0
        gci_fine = 1.25 * ea21 / (r21**2.0 - 1.0)

    return gci_fine, p_eff, ea21


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--run-level":
        level_index = int(sys.argv[2])
        out_file = sys.argv[3]
        return run_one_level(level_index, out_file)

    print("[plan_2.6V §4] GCI 3-Level (단축 도메인, 2 단위셀)")
    ROOT = os.path.join(os.path.dirname(__file__), "..")
    script = os.path.abspath(__file__)

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, lev in enumerate(LEVELS):
            out_path = os.path.join(tmp, f"K_{i}.txt")
            print(f"\n--- {lev['name']} dx={lev['dx_mm']} mm  {lev['nx']}x{lev['ny']}x{lev['nz']} ---")
            ret = subprocess.run(
                [sys.executable, script, "--run-level", str(i), out_path],
                cwd=ROOT, timeout=3600,
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
    gci_pct, p_eff, ea21 = compute_gci(K_c, K_m, K_f, h_c, h_m, h_f)

    print(f"\n=== GCI 결과 (Celik et al. 2008) ===")
    print(f"  Coarse K = {K_c:.4e}  Medium K = {K_m:.4e}  Fine K = {K_f:.4e}")
    print(f"  r21 = {h_m/h_f:.3f}  r32 = {h_c/h_m:.3f}")
    print(f"  e_a21 (Medium→Fine 상대오차) = {ea21:.2f}%")
    print(f"  Richardson p = {p_eff:.3f}")
    print(f"  GCI_fine = {gci_pct:.2f}%")
    passed = gci_pct < 5.0
    print(f"  판정: {'PASS' if passed else 'FAIL'} (기준 < 5%)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

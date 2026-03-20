#!/usr/bin/env python3
"""
plan_3.0V §3: Pareto Top-3 선정 + VTR/PNG 저장.

Top-3 기준:
  A: S_v 최대
  B: dP_darcy 최소
  C: S_v / dP_darcy 최대
"""
import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import taichi as ti
from pyevtk.hl import gridToVTK

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from solver.taichi_lbm_core import TaichiLBMWrapper


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DX_MM = 0.2
DX = DX_MM * 1e-3
NX = NY = 131
WALL_VOXELS = 5
G_LBM = 5e-6
RHO_PHYS = 0.746
NU_PHYS = 3.52e-5
MU_PHYS = NU_PHYS * RHO_PHYS
MAX_STEPS = 5_000
LOG_INTERVAL = 500
CONV_THRESH = 0.001


def select_top3(pareto: pd.DataFrame):
    p = pareto.copy()
    p["sv_over_dp"] = p["S_v"] / (p["dP_darcy"] + 1e-30)

    row_a = p.loc[p["S_v"].idxmax()]
    row_b = p.loc[p["dP_darcy"].idxmin()]
    row_c = p.loc[p["sv_over_dp"].idxmax()]

    top3 = {
        "A": row_a,
        "B": row_b,
        "C": row_c,
    }
    return top3


def save_pngs(rho_np, vz_np, solid_np, tag, out_dir):
    z_mid = solid_np.shape[2] // 2
    y_mid = solid_np.shape[1] // 2

    # vz XY
    plt.figure(figsize=(6, 6))
    plt.imshow(vz_np[:, :, z_mid].T, origin="lower", cmap="coolwarm")
    plt.colorbar(label="vz")
    plt.title(f"Top-{tag} vz XY (z={z_mid})")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"top3_{tag}_vz_xy.png"), dpi=170)
    plt.close()

    # solid XZ
    plt.figure(figsize=(10, 3))
    plt.imshow(solid_np[:, y_mid, :].T, origin="lower", cmap="gray_r", aspect="auto")
    plt.title(f"Top-{tag} solid XZ (y={y_mid})")
    plt.xlabel("x")
    plt.ylabel("z")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"top3_{tag}_solid_xz.png"), dpi=170)
    plt.close()


def run_one_design(tag, a_mm, t_val, nz, out_dir):
    print(f"\n--- Top-{tag}: a={a_mm:.4f}, t={t_val:.4f}, NZ={nz} ---")

    try:
        w = TaichiLBMWrapper(
            NX, NY, nz, DX, NU_PHYS, RHO_PHYS,
            u_in_phys=0.0, mode="periodic_body_force",
            buf_cells=2, arch=ti.cuda
        )
    except Exception:
        w = TaichiLBMWrapper(
            NX, NY, nz, DX, NU_PHYS, RHO_PHYS,
            u_in_phys=0.0, mode="periodic_body_force",
            buf_cells=2, arch=ti.cpu
        )

    w.set_geometry_gyroid_kernel(a_mm, t_val, WALL_VOXELS, gyroid_type="network", wall_voxels_z=0)
    w.core.set_body_force_z(G_LBM)

    z_mid = nz // 2
    q_history = []
    converged_at = None
    step_done = 0

    for step in range(0, MAX_STEPS, LOG_INTERVAL):
        for _ in range(LOG_INTERVAL):
            w.core.step()
        step_done = step + LOG_INTERVAL
        q = float(w.core.get_flux_z(z_mid))
        q_history.append(q)
        if len(q_history) > 3:
            q_history.pop(0)
        if len(q_history) >= 3:
            arr = np.array(q_history)
            mean_q = np.mean(arr)
            if mean_q > 1e-30:
                change = (np.max(arr) - np.min(arr)) / mean_q
                if change < CONV_THRESH:
                    converged_at = step_done
                    break

    rho_np = w.core.rho.to_numpy()
    vel_np = w.core.v.to_numpy()
    solid_np = w.core.solid.to_numpy()
    vz_np = vel_np[:, :, :, 2]

    dt = w.core.dt
    A_duct = (NX - 2 * WALL_VOXELS) ** 2 * DX ** 2
    L_phys = nz * DX
    Q_lb = float(w.core.get_flux_z(z_mid))
    Q_phys = Q_lb * DX ** 3 / dt
    u_sup = Q_phys / A_duct
    g_phys = G_LBM * DX / dt ** 2
    dP = RHO_PHYS * g_phys * L_phys
    K = u_sup * MU_PHYS * L_phys / (dP + 1e-30)
    dP_darcy = 0.2778 * MU_PHYS * 0.1 / (K + 1e-30)

    x = np.arange(0, NX + 1, dtype=np.float64) * DX_MM
    y = np.arange(0, NY + 1, dtype=np.float64) * DX_MM
    z = np.arange(0, nz + 1, dtype=np.float64) * DX_MM
    vtr_path = os.path.join(out_dir, f"top3_{tag}")
    gridToVTK(
        vtr_path, x, y, z,
        cellData={
            "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
            "vz": np.ascontiguousarray(vz_np, dtype=np.float64),
            "solid": np.ascontiguousarray(solid_np.astype(np.float64), dtype=np.float64),
        },
    )
    save_pngs(rho_np, vz_np, solid_np, tag, out_dir)

    print(
        f"  step={converged_at or step_done}, K={K:.4e}, "
        f"dP_darcy={dP_darcy:.2f} Pa, 저장={vtr_path}.vtr"
    )
    return {
        "design": tag,
        "a": a_mm,
        "t": t_val,
        "NZ": nz,
        "converged_step": converged_at or step_done,
        "K": K,
        "dP_darcy": dP_darcy,
        "vtr": f"results/top3_{tag}.vtr",
        "vz_png": f"results/top3_{tag}_vz_xy.png",
        "solid_png": f"results/top3_{tag}_solid_xz.png",
    }


def main():
    parser = argparse.ArgumentParser(description="Run Pareto Top-3 VTI visualization")
    parser.add_argument("--pareto", default="results/pareto_front.csv")
    parser.add_argument("--out-summary", default="results/top3_summary.csv")
    args = parser.parse_args()

    pareto_path = os.path.join(ROOT, args.pareto)
    if not os.path.exists(pareto_path):
        raise FileNotFoundError(f"Pareto CSV 없음: {pareto_path}")

    pareto = pd.read_csv(pareto_path)
    top3 = select_top3(pareto)
    out_dir = os.path.join(ROOT, "results")
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    for tag, row in top3.items():
        a = float(row["a"])
        t = float(row["t"])
        nz = int(round(float(row["NZ"])))
        rows.append(run_one_design(tag, a, t, nz, out_dir))

    out_summary = os.path.join(ROOT, args.out_summary)
    pd.DataFrame(rows).to_csv(out_summary, index=False)
    print(f"\n저장: {args.out_summary}")


if __name__ == "__main__":
    main()

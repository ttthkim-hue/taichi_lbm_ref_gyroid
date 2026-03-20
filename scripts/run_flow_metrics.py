#!/usr/bin/env python3
"""
plan_3.1V Phase 4: 유동 특성화 + VTI.
Top-5 설계의 혼합지표, 와도, 유속 불균일도 산출 + VTR/PNG 저장.

출력:
  results/flow_metrics.csv
  results/top5_{A~E}_vz_xy.png
  results/top5_{A~E}_vtrans_xy.png
  results/top5_{A~E}_omega_xy.png
"""
import argparse
import os
import sys
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


def compute_metrics(vel_np, solid_np, wv):
    """유동 특성 지표 계산."""
    fluid_mask = solid_np == 0
    interior = np.zeros_like(solid_np, dtype=bool)
    interior[wv:-wv, wv:-wv, :] = True
    mask = fluid_mask & interior

    vx = vel_np[:, :, :, 0][mask]
    vy = vel_np[:, :, :, 1][mask]
    vz = vel_np[:, :, :, 2][mask]

    v_trans = np.sqrt(vx ** 2 + vy ** 2)
    vz_abs = np.abs(vz)

    mixing_ratio = np.mean(v_trans) / (np.mean(vz_abs) + 1e-30)

    vz_nz = vz[vz_abs > 1e-10]
    if len(vz_nz) > 0:
        uniformity = float(np.std(vz_nz) / (np.mean(vz_nz) + 1e-30))
    else:
        uniformity = float("nan")

    v_mag = np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
    mean_vmag = np.mean(v_mag)
    mean_vz_abs = np.mean(vz_abs)
    tortuosity = mean_vmag / (mean_vz_abs + 1e-30)

    return {
        "mixing_ratio": mixing_ratio,
        "uniformity": uniformity,
        "tortuosity": tortuosity,
    }


def compute_omega_z(vel_np, solid_np):
    """Z-방향 와도 ω_z = ∂vy/∂x - ∂vx/∂y (중앙 차분)."""
    vy = vel_np[:, :, :, 1].astype(np.float64)
    vx = vel_np[:, :, :, 0].astype(np.float64)
    dvy_dx = np.gradient(vy, axis=0)
    dvx_dy = np.gradient(vx, axis=1)
    omega_z = dvy_dx - dvx_dy
    omega_z[solid_np == 1] = 0.0
    return omega_z


def save_flow_pngs(vel_np, solid_np, omega_z, tag, nz, out_dir):
    z_mid = nz // 2
    vx = vel_np[:, :, z_mid, 0]
    vy = vel_np[:, :, z_mid, 1]
    vz = vel_np[:, :, z_mid, 2]
    v_trans = np.sqrt(vx ** 2 + vy ** 2)
    solid_slice = solid_np[:, :, z_mid]

    v_trans[solid_slice == 1] = np.nan
    vz_plot = vz.copy()
    vz_plot[solid_slice == 1] = np.nan
    omega_slice = omega_z[:, :, z_mid].copy()
    omega_slice[solid_slice == 1] = np.nan

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    im0 = axes[0].imshow(vz_plot.T, origin="lower", cmap="coolwarm")
    axes[0].set_title(f"Top-{tag} vz XY (z={z_mid})")
    plt.colorbar(im0, ax=axes[0], label="vz")

    im1 = axes[1].imshow(v_trans.T, origin="lower", cmap="hot")
    axes[1].set_title(f"Top-{tag} v_trans XY")
    plt.colorbar(im1, ax=axes[1], label="v_trans")

    om_max = np.nanmax(np.abs(omega_slice)) + 1e-30
    im2 = axes[2].imshow(omega_slice.T, origin="lower", cmap="RdBu_r",
                         vmin=-om_max, vmax=om_max)
    axes[2].set_title(f"Top-{tag} ω_z XY")
    plt.colorbar(im2, ax=axes[2], label="omega_z")

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"top5_{tag}_flow.png"), dpi=170)
    plt.close(fig)

    for name, data, cmap in [
        ("vz_xy", vz_plot, "coolwarm"),
        ("vtrans_xy", v_trans, "hot"),
        ("omega_xy", omega_slice, "RdBu_r"),
    ]:
        plt.figure(figsize=(6, 6))
        if "omega" in name:
            plt.imshow(data.T, origin="lower", cmap=cmap, vmin=-om_max, vmax=om_max)
        else:
            plt.imshow(data.T, origin="lower", cmap=cmap)
        plt.colorbar()
        plt.title(f"Top-{tag} {name}")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"top5_{tag}_{name}.png"), dpi=170)
        plt.close()


def run_design(tag, a_mm, t_val, nz, eps_val, K_val, out_dir):
    import taichi as ti
    from solver.taichi_lbm_core import TaichiLBMWrapper

    print(f"\n--- Top-{tag}: a={a_mm:.2f}, t={t_val:.3f}, NZ={nz} ---")
    try:
        w = TaichiLBMWrapper(NX, NY, nz, DX, NU_PHYS, RHO_PHYS,
                             u_in_phys=0.0, mode="periodic_body_force",
                             buf_cells=2, arch=ti.cuda)
    except Exception:
        w = TaichiLBMWrapper(NX, NY, nz, DX, NU_PHYS, RHO_PHYS,
                             u_in_phys=0.0, mode="periodic_body_force",
                             buf_cells=2, arch=ti.cpu)

    w.set_geometry_gyroid_kernel(a_mm, t_val, WALL_VOXELS,
                                gyroid_type="network", wall_voxels_z=0)
    w.core.set_body_force_z(G_LBM)

    z_mid = nz // 2
    q_history = []
    for step in range(0, MAX_STEPS, LOG_INTERVAL):
        for _ in range(LOG_INTERVAL):
            w.core.step()
        Q_lb = float(w.core.get_flux_z(z_mid))
        q_history.append(Q_lb)
        if len(q_history) > 3:
            q_history.pop(0)
        if len(q_history) >= 3:
            arr = np.array(q_history)
            mn = np.mean(arr)
            if mn > 1e-30 and (np.max(arr) - np.min(arr)) / mn < CONV_THRESH:
                break

    vel_np = w.core.v.to_numpy()
    solid_np = w.core.solid.to_numpy()

    metrics = compute_metrics(vel_np, solid_np, WALL_VOXELS)
    omega_z = compute_omega_z(vel_np, solid_np)
    save_flow_pngs(vel_np, solid_np, omega_z, tag, nz, out_dir)

    dt = w.core.dt
    A_duct = (NX - 2 * WALL_VOXELS) ** 2 * DX ** 2
    Q_lb = float(w.core.get_flux_z(z_mid))
    Q_phys = Q_lb * DX ** 3 / dt
    u_sup = Q_phys / A_duct
    d_pore = np.sqrt(abs(K_val) / (eps_val + 1e-30))
    Re_pore = abs(u_sup) * d_pore * RHO_PHYS / MU_PHYS

    metrics["design"] = tag
    metrics["a"] = a_mm
    metrics["t"] = t_val
    metrics["Re_pore"] = Re_pore
    print(f"  mixing={metrics['mixing_ratio']:.4f}, "
          f"uniformity={metrics['uniformity']:.4f}, "
          f"tortuosity={metrics['tortuosity']:.4f}, Re={Re_pore:.4f}")
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Phase 4: Flow characterization")
    parser.add_argument("--pareto", default="results/campaign_plan31v/pareto_front.csv")
    parser.add_argument("--top5", default="results/campaign_plan31v/top5_selected.csv")
    parser.add_argument("--output", default="results/campaign_plan31v/flow_metrics.csv")
    args = parser.parse_args()

    top5_path = os.path.join(ROOT, args.top5)
    pareto_path = os.path.join(ROOT, args.pareto)
    if os.path.exists(top5_path):
        designs = pd.read_csv(top5_path)
    elif os.path.exists(pareto_path):
        pareto = pd.read_csv(pareto_path)
        designs = pareto.head(5).copy()
        designs["design"] = [chr(65 + i) for i in range(len(designs))]
    else:
        raise FileNotFoundError("Top-5/Pareto CSV 없음")

    out_dir = os.path.join(ROOT, "results")
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    for _, d in designs.iterrows():
        tag = str(d.get("design", "?"))
        a = float(d["a"])
        t_val = float(d["t"])
        eps_val = float(d.get("epsilon", 0.5))
        K_val = float(d.get("K", 1e-8))
        nz = max(10, round(2 * a / DX_MM))
        rows.append(run_design(tag, a, t_val, nz, eps_val, K_val, out_dir))

    out_path = os.path.join(ROOT, args.output)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\n[Phase 4] 유동 특성화 완료: {args.output}")


if __name__ == "__main__":
    main()

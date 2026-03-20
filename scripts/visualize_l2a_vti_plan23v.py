#!/usr/bin/env python3
"""
plan_2.3V §3.2: L2-A VTI(VTR) 시각화 — ParaView 확인 항목을 matplotlib로 생성.
Phase 3(Gyroid) 제외, Phase 2 시각화만 진행.

사용: python scripts/visualize_l2a_vti_plan23v.py [vtr_path]
  vtr_path 기본: results/l2a_diag_step7000.vtr (수렴 시점)
출력: results/plan23v_vis_*.png
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# L2-A 동일 (z_in, z_out = run_l2_ref6x6_plan17v / wrapper)
NX, NY, NZ = 131, 131, 550
BUF_CELLS = 2
Z_IN, Z_OUT = BUF_CELLS + 5, NZ - 1 - BUF_CELLS - 5  # 7, 542


def load_vtr(path):
    from vtk import vtkXMLRectilinearGridReader
    r = vtkXMLRectilinearGridReader()
    r.SetFileName(path)
    r.Update()
    g = r.GetOutput()
    dims = g.GetDimensions()  # (132, 132, 551) points
    nc = (dims[0] - 1) * (dims[1] - 1) * (dims[2] - 1)

    def get_cell_array(name):
        a = g.GetCellData().GetArray(name)
        if a is None:
            return None
        arr = np.array([a.GetValue(i) for i in range(a.GetNumberOfTuples())])
        return arr.reshape((dims[0] - 1, dims[1] - 1, dims[2] - 1), order="F")

    rho = get_cell_array("rho")
    vz = get_cell_array("vz")
    solid = get_cell_array("solid")
    return rho, vz, solid


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_run = "ref6x6_20260319_7k"  # 실행별 run_id 하위 폴더
    vtr_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "results", "l2a_vti", default_run, "l2a_diag_step7000.vtr")
    out_dir = os.path.join(root, "results", "plan23v_vis")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(vtr_path))[0]

    if not os.path.isfile(vtr_path):
        print(f"[visualize_l2a_vti] 파일 없음: {vtr_path}")
        return 1

    print(f"[visualize_l2a_vti] 로드: {vtr_path}")
    rho, vz, solid = load_vtr(vtr_path)
    # 유체 마스크 (solid==0)
    fluid = np.ones_like(rho, dtype=bool) if solid is None else (solid < 0.5)

    # 1) Z방향 ρ 분포 — XY 평균(유체만) ρ vs Z
    rho_z = np.zeros(NZ)
    for k in range(NZ):
        m = fluid[:, :, k]
        if m.any():
            rho_z[k] = rho[:, :, k][m].mean()
        else:
            rho_z[k] = np.nan
    fig, ax = plt.subplots(1, 1, figsize=(6, 3))
    ax.plot(np.arange(NZ) + 0.5, rho_z, "b-", lw=1)
    ax.axvline(Z_IN, color="gray", ls="--", label=f"z_in={Z_IN}")
    ax.axvline(Z_OUT, color="gray", ls=":", label=f"z_out={Z_OUT}")
    ax.set_xlabel("z (cell index)")
    ax.set_ylabel("ρ (XY mean, fluid)")
    ax.set_title("plan_2.3V §3.2: rho vs Z (inlet high, outlet low)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p1 = os.path.join(out_dir, f"plan23v_vis_1_rho_vs_z_{base}.png")
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print(f"  저장: {p1}")

    # 2) XY 단면 ρ (z = Z_OUT 부근)
    z_slice = Z_OUT
    rho_xy = np.where(fluid[:, :, z_slice], rho[:, :, z_slice], np.nan)
    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
    im = ax.imshow(rho_xy.T, origin="lower", aspect="equal", cmap="viridis",
                   extent=(0, NX, 0, NY), vmin=rho[fluid].min(), vmax=rho[fluid].max())
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.set_title(f"plan_2.3V §3.2: XY slice rho (z={z_slice})")
    plt.colorbar(im, ax=ax, label="ρ")
    fig.tight_layout()
    p2 = os.path.join(out_dir, f"plan23v_vis_2_rho_xy_z{z_slice}_{base}.png")
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print(f"  저장: {p2}")

    # 3) XY 단면 vz (z = NZ//2)
    z_mid = NZ // 2
    vz_xy = np.where(fluid[:, :, z_mid], vz[:, :, z_mid], np.nan)
    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
    im = ax.imshow(vz_xy.T, origin="lower", aspect="equal", cmap="plasma",
                   extent=(0, NX, 0, NY))
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.set_title(f"plan_2.3V §3.2: XY slice vz (z={z_mid})")
    plt.colorbar(im, ax=ax, label="vz")
    fig.tight_layout()
    p3 = os.path.join(out_dir, f"plan23v_vis_3_vz_xy_z{z_mid}_{base}.png")
    fig.savefig(p3, dpi=150)
    plt.close(fig)
    print(f"  저장: {p3}")

    # 4) z_in, z_out 슬라이스 ρ (유체 셀 ρ 차이)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    for ax, z, title in zip(axes, [Z_IN, Z_OUT], [f"z_in={Z_IN}", f"z_out={Z_OUT}"]):
        r = np.where(fluid[:, :, z], rho[:, :, z], np.nan)
        im = ax.imshow(r.T, origin="lower", aspect="equal", cmap="viridis",
                       extent=(0, NX, 0, NY), vmin=rho[fluid].min(), vmax=rho[fluid].max())
        ax.set_title(title)
        ax.set_xlabel("x"); ax.set_ylabel("y")
        plt.colorbar(im, ax=ax, label="ρ")
    fig.suptitle("plan_2.3V §3.2: z_in / z_out slice rho")
    fig.tight_layout()
    p4 = os.path.join(out_dir, f"plan23v_vis_4_slices_rho_{base}.png")
    fig.savefig(p4, dpi=150)
    plt.close(fig)
    print(f"  저장: {p4}")

    # 5) 채널 중심선 ρ(z) — (65,65)는 벽일 수 있음. 유체인 (13,13) 등 채널 중심 사용
    # 6×6 채널: 한 채널 중심 대략 (13, 13), (38, 13), ... (13,13)이 유체인지 확인
    i0, j0 = 13, 13
    if not fluid[i0, j0, Z_IN]:
        i0, j0 = 63, 63  # 다른 채널
    rho_center = rho[i0, j0, :].copy()
    rho_center[~fluid[i0, j0, :]] = np.nan
    fig, ax = plt.subplots(1, 1, figsize=(6, 3))
    ax.plot(np.arange(NZ) + 0.5, rho_center, "b-", lw=1)
    ax.axvline(Z_IN, color="gray", ls="--"); ax.axvline(Z_OUT, color="gray", ls=":")
    ax.set_xlabel("z (cell index)")
    ax.set_ylabel("ρ")
    ax.set_title(f"plan_2.3V §3.2: channel centerline rho(z) (i,j)=({i0},{j0})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    p5 = os.path.join(out_dir, f"plan23v_vis_5_rho_centerline_{base}.png")
    fig.savefig(p5, dpi=150)
    plt.close(fig)
    print(f"  저장: {p5}")

    print(f"[visualize_l2a_vti] 완료. 출력: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

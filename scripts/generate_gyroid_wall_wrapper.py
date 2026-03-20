#!/usr/bin/env python3
"""
V3.1 이슈3: Gyroid 올바른 외벽 — 내부 23.4mm(117셀)에만 gyroid 생성 후
외벽 5+5셀 + Z버퍼 10+10셀 래핑 → 127×127×570.

사용: generate_gyroid_openlb.generate_gyroid_array 호출 시
     내부 도메인(0.0234, 0.0234, 0.11)으로 117×117×550 생성한 뒤 패딩.
"""
import numpy as np
import os

# 내부 도메인: 23.4mm × 23.4mm × 110mm (117×117×550 @ 0.2mm)
L_INNER_X_M = 0.0234
L_INNER_Y_M = 0.0234
L_INNER_Z_M = 0.11
N_INNER_X = 117
N_INNER_Y = 117
N_INNER_Z = 550
WALL = 5
BUF_Z = 10


def generate_gyroid_inner_domain(nx: int, ny: int, nz: int, a_mm: float, t: float,
                                 L_x: float, L_y: float, L_z: float) -> np.ndarray:
    """Gyroid in inner domain only (0=fluid, 1=solid). Same formula as OpenLB."""
    dx = L_x / nx
    dy = L_y / ny
    dz = L_z / nz
    x = np.linspace(0, L_x, nx, endpoint=False) + dx / 2
    y = np.linspace(0, L_y, ny, endpoint=False) + dy / 2
    z = np.linspace(0, L_z, nz, endpoint=False) + dz / 2
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    L = a_mm / 1000.0
    val = (
        np.sin(2 * np.pi * X / L) * np.cos(2 * np.pi * Y / L)
        + np.sin(2 * np.pi * Y / L) * np.cos(2 * np.pi * Z / L)
        + np.sin(2 * np.pi * Z / L) * np.cos(2 * np.pi * X / L)
    )
    T_LEVEL_AT_T0 = 0.768
    t_level = T_LEVEL_AT_T0 + 0.35 * np.clip(float(t), -1.0, 1.0)
    mask = np.zeros((nx, ny, nz), dtype=np.uint8)
    mask[np.abs(val) < t_level] = 1
    return mask


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Gyroid 117×117×550 inner + wall+buffer → 127×127×570")
    ap.add_argument("--a", type=float, default=5.0)
    ap.add_argument("--t", type=float, default=0.0)
    ap.add_argument("--out", type=str, default="/mnt/h/openlb_gyroid/results/gate_a/gyroid_dx02_wall_buf_v31.npy")
    args = ap.parse_args()

    inner = generate_gyroid_inner_domain(
        N_INNER_X, N_INNER_Y, N_INNER_Z, args.a, args.t,
        L_INNER_X_M, L_INNER_Y_M, L_INNER_Z_M
    )
    # 127×127×570: 외벽 5+5, Z 버퍼 10+10
    out = np.ones((127, 127, 570), dtype=np.int32)
    out[WALL:127 - WALL, WALL:127 - WALL, BUF_Z:BUF_Z + N_INNER_Z] = inner
    out[:, :, :BUF_Z] = 0
    out[:, :, 570 - BUF_Z:] = 0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    np.save(args.out, out)
    print(f"Saved {args.out}  shape={out.shape}")
    print(f"  X=0  solid: {out[0,:,300].mean():.2f}  X=-1: {out[-1,:,300].mean():.2f}")
    print(f"  Y=0  solid: {out[:,0,300].mean():.2f}  Y=-1: {out[:,-1,300].mean():.2f}")
    print(f"  Z buf 0..9 fluid: {(out[:,:, :BUF_Z]==0).all()}")
    print(f"  Z buf 560..569 fluid: {(out[:,:, 570-BUF_Z:]==0).all()}")


if __name__ == "__main__":
    main()

from __future__ import annotations

"""
Reference 채널용 Taichi LBM 실행 스켈레톤.

역할:
  - OpenLB MN .dat (ref_dx02 등)에서 형상 로딩
  - UnitConverter로 dx, dt, tau, Ma 설정
  - Taichi 필드 할당 및 기본 루프 구조 정의 (세부 커널은 추후 구현)
  - 수렴 후 postprocess.compute_darcy_from_fields 호출해 JSON 저장
"""

import argparse
from pathlib import Path

import numpy as np

from unit_converter import from_openlb_like
from geometry_io import read_mn_dat
from postprocess import DarcyResult, compute_darcy_from_fields, save_result_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", type=str, required=True, help="OpenLB MN .dat path (e.g. ref_dx02.dat)")
    ap.add_argument("--dx", type=float, default=0.0002, help="Grid spacing [m]")
    ap.add_argument("--u_in", type=float, default=0.2778, help="Inlet velocity [m/s]")
    ap.add_argument("--L", type=float, default=0.1, help="Channel length [m]")
    ap.add_argument("--nu", type=float, default=3.52e-5, help="Kinematic viscosity [m^2/s]")
    ap.add_argument("--rho", type=float, default=0.746, help="Density [kg/m^3]")
    ap.add_argument("--tau", type=float, default=0.557, help="Lattice relaxation time")
    ap.add_argument("--out", type=str, default="result_taichi_ref_dx02.json")
    args = ap.parse_args()

    dat_path = Path(args.dat)
    geom = read_mn_dat(dat_path)

    # resolution은 z 방향 길이에 맞추어 설정 (OpenLB gyroid_perm과 유사)
    resolution = geom.nz
    converter = from_openlb_like(
        L_catalyst=args.L,
        u_inlet=args.u_in,
        nu=args.nu,
        rho=args.rho,
        nz=resolution,
        tau=args.tau,
    )
    print(converter.summary())

    # TODO: Taichi 필드(f, rho, ux, uy, uz 등) 초기화 및 LBM time stepping 구현
    # 여기서는 구조만 정의하고, 실행 후 postprocess 단계 예시를 보여준다.

    # Placeholder: 균일 속도장/압력차 0으로부터 DarcyResult 생성 예시
    u_z_phys = np.zeros((geom.nx, geom.ny, geom.nz), dtype=float)
    vals = compute_darcy_from_fields(
        u_z_phys=u_z_phys,
        p_inlet=0.0,
        p_outlet=0.0,
        rho=args.rho,
        mu=args.nu * args.rho,
        L=args.L,
    )
    result = DarcyResult(
        K_m2=vals["K_m2"],
        deltaP_Pa=vals["deltaP_Pa"],
        CV=vals["CV"],
        converged=False,
        steps=0,
        u_avg=vals["u_avg"],
    )
    save_result_json(args.out, result)


if __name__ == "__main__":
    main()


from __future__ import annotations

"""
OpenLB 스타일 UnitConverter를 단순화해 Taichi LBM에서 재사용하기 위한 모듈.

입력:
    phys_L   : 특성 길이 [m] (예: 채널 길이 L_catalyst)
    phys_U   : 특성 속도 [m/s] (예: u_inlet)
    nu_phys  : 물리 점성 계수 [m^2/s]
    rho_phys : 물리 밀도 [kg/m^3]
    resolution: 격자 해상도 (예: NZ)
    tau      : 격자 relaxation time (기본 None → ν로부터 계산)

출력/프로퍼티:
    dx, dt, u_latt, nu_latt, Ma, Re 등
"""

import math
from dataclasses import dataclass


@dataclass
class UnitConverter:
    phys_L: float
    phys_U: float
    nu_phys: float
    rho_phys: float
    resolution: int
    tau: float | None = None

    def __post_init__(self) -> None:
        if self.resolution <= 0:
            raise ValueError("resolution must be positive")
        self.dx = self.phys_L / float(self.resolution)

        if self.tau is not None:
            # tau가 주어지면 dt를 역으로 계산
            self.dt = (self.tau - 0.5) * self.dx**2 / (3.0 * self.nu_phys)
        else:
            # dt를 phys_U 기준으로 추정하고 tau가 0.55~1.0 범위에 오도록 조정
            # 초기 dt: CFL ~ 0.03 수준을 목표 (OpenLB gyroid_perm 유사)
            cfl_target = 0.03
            self.dt = cfl_target * self.dx / max(self.phys_U, 1e-12)
            nu_lb = self.nu_phys * self.dt / self.dx**2
            tau_raw = 3.0 * nu_lb + 0.5
            # 안정 범위로 클램프
            tau_min, tau_max = 0.55, 1.0
            self.tau = min(max(tau_raw, tau_min), tau_max)
            # 클램프된 tau에 맞게 dt 재계산
            self.dt = (self.tau - 0.5) * self.dx**2 / (3.0 * self.nu_phys)

        # 격자 단위 점성, 속도, 무차원수 계산
        self.nu_latt = self.nu_phys * self.dt / self.dx**2
        self.u_latt = self.phys_U * self.dt / self.dx
        self.Ma = self.u_latt * math.sqrt(3.0)  # cs = 1/sqrt(3)

        # 특성 길이/속도로부터 Re 계산 (물리 단위에서)
        self.Re = self.rho_phys * self.phys_U * self.phys_L / (self.nu_phys * self.rho_phys)

    @property
    def omega(self) -> float:
        return 1.0 / self.tau

    def summary(self) -> str:
        return (
            f"UnitConverter:\n"
            f"  L={self.phys_L:.4g} m, U={self.phys_U:.4g} m/s, nu={self.nu_phys:.3e} m^2/s, rho={self.rho_phys:.3g} kg/m^3\n"
            f"  resolution={self.resolution}, dx={self.dx:.3e} m, dt={self.dt:.3e} s\n"
            f"  tau={self.tau:.4f}, omega={self.omega:.4f}, u_latt={self.u_latt:.5f}, Ma={self.Ma:.4f}, Re={self.Re:.1f}\n"
        )


def from_openlb_like(
    L_catalyst: float,
    u_inlet: float,
    nu: float,
    rho: float,
    nz: int,
    tau: float | None = None,
) -> UnitConverter:
    """
    OpenLB gyroid_perm 설정을 그대로 옮겨오기 위한 헬퍼.
    """
    return UnitConverter(
        phys_L=L_catalyst,
        phys_U=u_inlet,
        nu_phys=nu,
        rho_phys=rho,
        resolution=nz,
        tau=tau,
    )


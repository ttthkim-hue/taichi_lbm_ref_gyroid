"""
D3Q19 MRT-LBM core (taichi_LBM3D 구조 채용).
- 충돌: D3Q19 MRT (M, S, meq). 스트리밍: push + bounce-back.
- 기하: Voxel(0=Fluid, 1=Solid) Numpy → geometry field 매핑.
- BC: Inlet(Z=0) 지정 속도 U_in, Outlet(Z=NZ-1) 고정 압력(Zero-gradient) 역류 방지.
- BO 연동: Wrapper.run(steps) → Delta P [Pa] float 반환.

참조: https://github.com/yjhp1016/taichi_LBM3D (Single_phase)
"""

import taichi as ti
import numpy as np

# D3Q19 벡터 (taichi_LBM3D 순서)
E_NP = np.array([
    [0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1],
    [1, 1, 0], [-1, -1, 0], [1, -1, 0], [-1, 1, 0],
    [1, 0, 1], [-1, 0, -1], [1, 0, -1], [-1, 0, 1],
    [0, 1, 1], [0, -1, -1], [0, 1, -1], [0, -1, 1]
], dtype=np.int32)
# 반대 방향 (bounce-back)
LR_NP = np.array([0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15, 18, 17], dtype=np.int32)
# 가중치
W_NP = np.array([1/3, 1/18, 1/18, 1/18, 1/18, 1/18, 1/18,
                 1/36, 1/36, 1/36, 1/36, 1/36, 1/36, 1/36, 1/36, 1/36, 1/36, 1/36, 1/36], dtype=np.float64)
# M 행렬 (taichi_LBM3D LBM_3D_SinglePhase_Solver / lbm_solver_3d)
M_NP = np.array([
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [-1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, -2, -2, -2, -2, -2, -2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, -1, 0, 0, 0, 0, 1, -1, 1, -1, 1, -1, 1, -1, 0, 0, 0, 0],
    [0, -2, 2, 0, 0, 0, 0, 1, -1, 1, -1, 1, -1, 1, -1, 0, 0, 0, 0],
    [0, 0, 0, 1, -1, 0, 0, 1, -1, -1, 1, 0, 0, 0, 0, 1, -1, 1, -1],
    [0, 0, 0, -2, 2, 0, 0, 1, -1, -1, 1, 0, 0, 0, 0, 1, -1, 1, -1],
    [0, 0, 0, 0, 0, 1, -1, 0, 0, 0, 0, 1, -1, -1, 1, 1, -1, -1, 1],
    [0, 0, 0, 0, 0, -2, 2, 0, 0, 0, 0, 1, -1, -1, 1, 1, -1, -1, 1],
    [0, 2, 2, -1, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, -2, -2, -2, -2],
    [0, -2, -2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -2, -2, -2, -2],
    [0, 0, 0, 1, 1, -1, -1, 1, 1, 1, 1, -1, -1, -1, -1, 0, 0, 0, 0],
    [0, 0, 0, -1, -1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, -1, -1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, -1, -1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, -1, 1, -1, -1, 1, -1, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, -1, 1, 1, -1, 0, 0, 0, 0, 1, -1, 1, -1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, -1, -1, 1, -1, 1, 1, -1]
], dtype=np.float64)
INV_M_NP = np.linalg.inv(M_NP)


@ti.data_oriented
class TaichiLBMCore:
    """D3Q19 MRT 코어. geometry는 set_geometry_from_voxel()로 설정."""

    def __init__(self, nx: int, ny: int, nz: int, dx: float, nu_phys: float, rho_phys: float,
                 u_in_phys: float = 0.2778, tau: float = 0.595, periodic_z: bool = False,
                 body_force_z: float = 0.0, arch=ti.cuda):
        self.nx, self.ny, self.nz = nx, ny, nz
        self.dx = dx
        self.nu_phys = nu_phys
        self.rho_phys = rho_phys
        self.u_in_phys = u_in_phys
        self.tau = tau
        self.periodic_z = periodic_z
        self.body_force_z = body_force_z
        # plan_1.9V §2.1: dt를 τ 기반 고정 (u_in에 의존하지 않음)
        self.nu_lb = (tau - 0.5) / 3.0
        self.dt = self.nu_lb * (dx ** 2) / nu_phys
        self.u_lb_in = u_in_phys * self.dt / self.dx
        # Ma 안전 검사
        Ma = self.u_lb_in * (3.0 ** 0.5)
        if Ma >= 0.3:
            raise ValueError(f"Ma={Ma:.3f} >= 0.3 (u_in={u_in_phys}, dt={self.dt:.2e})")
        # 압력 스케일 [Pa per lattice rho]
        self.cs2_phys = (1.0 / 3.0) * (self.dx / self.dt) ** 2
        self.p_scale = rho_phys * self.cs2_phys

        ti.init(arch=arch, default_fp=ti.f64)
        # S_dig (MRT relaxation)
        s_v = 1.0 / tau
        s_other = 8.0 * (2.0 - s_v) / (8.0 - s_v)
        self.S_dig_np = np.array([
            0, s_v, s_v, 0, s_other, 0, s_other, 0, s_other,
            s_v, s_v, s_v, s_v, s_v, s_v, s_v, s_other, s_other, s_other
        ], dtype=np.float64)

        self.f = ti.Vector.field(19, ti.f64, shape=(nx, ny, nz))
        self.F = ti.Vector.field(19, ti.f64, shape=(nx, ny, nz))
        self.rho = ti.field(ti.f64, shape=(nx, ny, nz))
        self.v = ti.Vector.field(3, ti.f64, shape=(nx, ny, nz))
        self.solid = ti.field(ti.i32, shape=(nx, ny, nz))
        self.e = ti.Vector.field(3, ti.i32, shape=19)
        self.w = ti.field(ti.f64, shape=19)
        self.LR = ti.field(ti.i32, shape=19)
        self.M = ti.field(ti.f64, shape=(19, 19))
        self.inv_M = ti.field(ti.f64, shape=(19, 19))
        self.S_dig = ti.field(ti.f64, shape=19)
        self.outlet_clip_count = ti.field(ti.i32, shape=())
        # plan_1.9V §3.2: 주기BC·체적력 (커널에서 읽기 위해 스칼라 필드)
        self._periodic_z = ti.field(ti.i32, shape=())
        self._body_force_z = ti.field(ti.f64, shape=())
        self._periodic_z[None] = 1 if periodic_z else 0
        self._body_force_z[None] = float(body_force_z)

        self.e.from_numpy(E_NP)
        self.w.from_numpy(W_NP)
        self.LR.from_numpy(LR_NP)
        self.S_dig.from_numpy(self.S_dig_np)
        self.M.from_numpy(M_NP)
        self.inv_M.from_numpy(INV_M_NP)

        ti.static(self.M)
        ti.static(self.inv_M)
        ti.static(self.S_dig)
        self._static_done = False

    def print_S_dig_consistency(self) -> bool:
        """
        plan_1.3V §1: S 대각 벡터 출력 및 보존량 점검.
        s₀,s₃,s₅,s₇ = 0.0 (질량·운동량 보존), s₉~s₁₃ = 1/τ.
        """
        S = self.S_dig_np
        inv_tau = 1.0 / self.tau
        print("[S_dig] 19 diagonal values:", S.tolist())
        ok = True
        for idx, name in [(0, "s₀ ρ"), (3, "s₃ jx"), (5, "s₅ jy"), (7, "s₇ jz")]:
            if S[idx] != 0.0:
                print(f"  ❌ {name} = {S[idx]} (must be 0.0)")
                ok = False
            else:
                print(f"  ✅ {name} = 0.0")
        for idx in range(9, 14):
            if abs(S[idx] - inv_tau) > 1e-6:
                print(f"  ❌ S[{idx}] = {S[idx]} (expected 1/τ = {inv_tau})")
                ok = False
        if ok:
            print(f"  ✅ s₉~s₁₃ = 1/τ = {inv_tau:.4f}")
        return ok

    @ti.func
    def feq(self, k: ti.i32, rho_local: ti.f64, u: ti.types.vector(3, ti.f64)) -> ti.f64:
        eu = self.e[k][0] * u[0] + self.e[k][1] * u[1] + self.e[k][2] * u[2]
        uv = u[0] * u[0] + u[1] * u[1] + u[2] * u[2]
        return self.w[k] * rho_local * (1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * uv)

    @ti.func
    def meq_vec(self, rho_local: ti.f64, u: ti.types.vector(3, ti.f64)):
        out = ti.Vector.zero(ti.f64, 19)
        out[0] = rho_local
        out[1] = u[0] * u[0] + u[1] * u[1] + u[2] * u[2]
        out[3] = u[0]
        out[5] = u[1]
        out[7] = u[2]
        out[9] = 2 * u[0] * u[0] - u[1] * u[1] - u[2] * u[2]
        out[11] = u[1] * u[1] - u[2] * u[2]
        out[13] = u[0] * u[1]
        out[14] = u[1] * u[2]
        out[15] = u[0] * u[2]
        return out

    @ti.kernel
    def _init_fields(self):
        for i, j, k in self.rho:
            if self.solid[i, j, k] == 0:
                self.rho[i, j, k] = 1.0
                self.v[i, j, k] = ti.Vector([0.0, 0.0, 0.0])
                for s in ti.static(range(19)):
                    feq_s = self.feq(s, 1.0, self.v[i, j, k])
                    self.f[i, j, k][s] = feq_s
                    self.F[i, j, k][s] = feq_s
            else:
                self.rho[i, j, k] = 1.0
                self.v[i, j, k] = ti.Vector([0.0, 0.0, 0.0])

    @ti.func
    def _guo_force_source_raw(self, s: ti.i32, u: ti.types.vector(3, ti.f64), g_z: ti.f64) -> ti.f64:
        """Guo et al. velocity-space source (Phys. Rev. E 65, 046308). (I-S/2)는 충돌 단계에서 moment space에서 적용."""
        cs2 = 1.0 / 3.0
        cs4 = cs2 * cs2
        eu = self.e[s][0] * u[0] + self.e[s][1] * u[1] + self.e[s][2] * u[2]
        term1 = (self.e[s][2] - u[2]) / cs2
        term2 = eu * self.e[s][2] / cs4
        return self.w[s] * (term1 + term2) * g_z

    @ti.kernel
    def _collision(self):
        for i, j, k in self.rho:
            if self.solid[i, j, k] != 0:
                continue
            m_temp = ti.Vector.zero(ti.f64, 19)
            for idx in ti.static(range(19)):
                for s in ti.static(range(19)):
                    m_temp[idx] += self.M[idx, s] * self.F[i, j, k][s]
            meq = self.meq_vec(self.rho[i, j, k], self.v[i, j, k])
            for s in ti.static(range(19)):
                m_temp[s] -= self.S_dig[s] * (m_temp[s] - meq[s])
            for s in ti.static(range(19)):
                self.f[i, j, k][s] = 0.0
                for l in ti.static(range(19)):
                    self.f[i, j, k][s] += self.inv_M[s, l] * m_temp[l]
            # plan_2.2V: Guo forcing MRT 호환 — moment space에서 (I - S_dig/2) 적용
            # 보존 moment(0,3,5,7) s=0 → factor 1.0, 응력 moment s=1/τ → factor (1-1/(2τ))
            g_z = self._body_force_z[None]
            if ti.abs(g_z) > 1e-20:
                u = self.v[i, j, k]
                S_vec = ti.Vector.zero(ti.f64, 19)
                for s in ti.static(range(19)):
                    S_vec[s] = self._guo_force_source_raw(s, u, g_z)
                m_force = ti.Vector.zero(ti.f64, 19)
                for idx in ti.static(range(19)):
                    for s in ti.static(range(19)):
                        m_force[idx] += self.M[idx, s] * S_vec[s]
                m_adj = ti.Vector.zero(ti.f64, 19)
                for idx in ti.static(range(19)):
                    m_adj[idx] = (1.0 - 0.5 * self.S_dig[idx]) * m_force[idx]
                for s in ti.static(range(19)):
                    F_add = 0.0
                    for l in ti.static(range(19)):
                        F_add += self.inv_M[s, l] * m_adj[l]
                    self.f[i, j, k][s] += F_add

    @ti.kernel
    def _streaming(self):
        # Push streaming (taichi_LBM3D): F[ip,s] = f[i,s]. plan_1.9V §3.2: Z 주기 래핑.
        for i, j, k in self.rho:
            if self.solid[i, j, k] == 0:
                for s in ti.static(range(19)):
                    self.F[i, j, k][s] = 0.0
        for i, j, k in self.rho:
            if self.solid[i, j, k] != 0:
                continue
            for s in ti.static(range(19)):
                ei = self.e[s]
                ip = i + ei[0]
                jp = j + ei[1]
                kp = k + ei[2]
                if self._periodic_z[None] != 0:
                    if kp >= self.nz:
                        kp = 0
                    elif kp < 0:
                        kp = self.nz - 1
                if 0 <= ip < self.nx and 0 <= jp < self.ny and 0 <= kp < self.nz:
                    if self.solid[ip, jp, kp] == 0:
                        self.F[ip, jp, kp][s] = self.f[i, j, k][s]
                    else:
                        rev = self.LR[s]
                        self.F[i, j, k][rev] = self.f[i, j, k][s]
                else:
                    rev = self.LR[s]
                    self.F[i, j, k][rev] = self.f[i, j, k][s]

    @ti.kernel
    def _bc_inlet_outlet(self):
        # plan_1.9V §3.2: 주기BC 시 inlet/outlet 비활성화 (Taichi 커널에서 return 불가 → 조건부 실행)
        if self._periodic_z[None] == 0:
            u_in = ti.Vector([0.0, 0.0, self.u_lb_in])
            for i, j in ti.ndrange(self.nx, self.ny):
                if self.solid[i, j, 0] == 0:
                    for s in ti.static(range(19)):
                        self.F[i, j, 0][s] = self.feq(s, 1.0, u_in)
            for i, j in ti.ndrange(self.nx, self.ny):
                if self.solid[i, j, self.nz - 1] == 0:
                    rho_out = 1.0
                    u_out = self.v[i, j, self.nz - 2]
                    if u_out[2] < 0.0:
                        ti.atomic_add(self.outlet_clip_count[None], 1)
                        u_out[2] = 0.0
                    for s in ti.static(range(19)):
                        self.F[i, j, self.nz - 1][s] = self.feq(s, rho_out, u_out)

    @ti.kernel
    def _copy_F_to_f_and_macro(self):
        for i, j, k in self.rho:
            if self.solid[i, j, k] != 0:
                continue
            for s in ti.static(range(19)):
                self.f[i, j, k][s] = self.F[i, j, k][s]
            r = 0.0
            jx = 0.0
            jy = 0.0
            jz = 0.0
            for s in ti.static(range(19)):
                fv = self.f[i, j, k][s]
                r += fv
                jx += fv * self.e[s][0]
                jy += fv * self.e[s][1]
                jz += fv * self.e[s][2]
            self.rho[i, j, k] = r
            inv_r = 1.0 / r
            self.v[i, j, k][0] = jx * inv_r
            self.v[i, j, k][1] = jy * inv_r
            self.v[i, j, k][2] = jz * inv_r

    def set_geometry_from_voxel(self, voxel_np: np.ndarray) -> None:
        """
        Voxel 데이터(0=Fluid, 1=Solid)를 LBM 도메인 geometry field에 매핑.
        voxel_np.shape == (nx, ny, nz), dtype 정수 또는 bool.
        """
        v = np.asarray(voxel_np).astype(np.int32)
        if v.shape != (self.nx, self.ny, self.nz):
            raise ValueError(f"voxel shape {v.shape} != ({self.nx}, {self.ny}, {self.nz})")
        self.solid.from_numpy(v)
        if not self._static_done:
            self._init_fields()
            self._static_done = True

    @ti.kernel
    def _init_gyroid_duct_kernel(self, a_mm: ti.f64, t: ti.f64, dx_mm: ti.f64, wall_voxels: ti.i32, use_network: ti.i32, wall_voxels_z: ti.i32):
        """
        plan_1.3V §6 / plan_2.5V §3 / plan_2.6V §1.3: Gyroid 수식 직접 평가.
        φ = sin(2πx/a)·cos(2πy/a) + ... 
        use_network=0 (Sheet): solid=1 if |φ|<t
        use_network=1 (Network): solid=1 if φ>-t (유체 φ<-t, Z 관통 보장)
        wall_voxels_z: Z 방향 외벽 voxel 수 (주기BC에서는 0)
        """
        for i, j, k in self.solid:
            if i < wall_voxels or i >= self.nx - wall_voxels or j < wall_voxels or j >= self.ny - wall_voxels or (wall_voxels_z > 0 and (k < wall_voxels_z or k >= self.nz - wall_voxels_z)):
                self.solid[i, j, k] = 1
            else:
                x_mm = (i + 0.5) * dx_mm
                y_mm = (j + 0.5) * dx_mm
                z_mm = (k + 0.5) * dx_mm
                pi2_a = 2.0 * 3.14159265358979 / a_mm
                phi = ti.sin(pi2_a * x_mm) * ti.cos(pi2_a * y_mm) + ti.sin(pi2_a * y_mm) * ti.cos(pi2_a * z_mm) + ti.sin(pi2_a * z_mm) * ti.cos(pi2_a * x_mm)
                if use_network != 0:
                    self.solid[i, j, k] = 1 if phi > (-t) else 0
                else:
                    self.solid[i, j, k] = 1 if ti.abs(phi) < t else 0

    def set_geometry_gyroid_kernel(self, a_mm: float, t: float, wall_voxels: int = 5, gyroid_type: str = "network", wall_voxels_z: int = -1) -> None:
        """
        Gyroid 수식으로 solid 필드 채움. plan_2.5V §3: gyroid_type "network" 시 Z 관통.
        gyroid_type: "sheet" (|φ|<t 고체) | "network" (φ>-t 고체, 유체 φ<-t)
        wall_voxels_z: Z 방향 외벽 voxel 수. -1이면 wall_voxels와 동일. 주기BC에서는 0으로 설정.
        """
        dx_mm = float(self.dx * 1000.0)
        use_network = 1 if (gyroid_type or "network").lower() == "network" else 0
        wv_z = wall_voxels if wall_voxels_z < 0 else wall_voxels_z
        self._init_gyroid_duct_kernel(a_mm, t, dx_mm, wall_voxels, use_network, wv_z)
        if not self._static_done:
            self._init_fields()
            self._static_done = True

    def step(self) -> None:
        self._collision()
        self._streaming()
        self._bc_inlet_outlet()
        self._copy_F_to_f_and_macro()

    @ti.kernel
    def _slice_rho_mean(self, z_in: ti.i32, z_out: ti.i32) -> ti.types.vector(2, ti.f64):
        r0 = 0.0
        r1 = 0.0
        c0 = 0.0
        c1 = 0.0
        for i, j in ti.ndrange(self.nx, self.ny):
            if self.solid[i, j, z_in] == 0:
                r0 += self.rho[i, j, z_in]
                c0 += 1.0
            if self.solid[i, j, z_out] == 0:
                r1 += self.rho[i, j, z_out]
                c1 += 1.0
        avg0 = r0 / c0 if c0 > 0 else 1.0
        avg1 = r1 / c1 if c1 > 0 else 1.0
        return ti.Vector([avg0, avg1])

    def get_delta_p_lattice(self, z_in: int, z_out: int) -> float:
        v = self._slice_rho_mean(z_in, z_out)
        return float(v[0] - v[1])

    def get_delta_p_pascal(self, z_in: int, z_out: int) -> float:
        return self.get_delta_p_lattice(z_in, z_out) * self.p_scale

    def reset_outlet_clip_count(self) -> None:
        self.outlet_clip_count[None] = 0

    def get_outlet_clip_count(self) -> int:
        return int(self.outlet_clip_count[None])

    @ti.kernel
    def _total_mass(self) -> ti.f64:
        s = 0.0
        for i, j, k in self.rho:
            if self.solid[i, j, k] == 0:
                s += self.rho[i, j, k]
        return s

    @ti.kernel
    def _flux_z_plane(self, z: ti.i32) -> ti.f64:
        q = 0.0
        for i, j in ti.ndrange(self.nx, self.ny):
            if self.solid[i, j, z] == 0:
                q += self.rho[i, j, z] * self.v[i, j, z][2]
        return q

    @ti.kernel
    def _max_velocity(self) -> ti.f64:
        m = 0.0
        for i, j, k in self.rho:
            if self.solid[i, j, k] == 0:
                u2 = self.v[i, j, k][0] ** 2 + self.v[i, j, k][1] ** 2 + self.v[i, j, k][2] ** 2
                if u2 > m:
                    m = u2
        return ti.sqrt(m)

    def get_total_mass(self) -> float:
        return float(self._total_mass())

    def get_flux_z(self, z: int) -> float:
        return float(self._flux_z_plane(z))

    def get_max_velocity(self) -> float:
        return float(self._max_velocity())

    def set_body_force_z(self, g_lbm: float) -> None:
        """plan_1.9V §3.2: 체적력 Z (격자 단위) 설정."""
        self._body_force_z[None] = float(g_lbm)


class TaichiLBMWrapper:
    """
    BO 최적화 루프 연동용 래퍼.
    시뮬레이션 종료 후 Inlet·Outlet 단면 평균 압력차(Delta P) [Pa]를 float로 반환.
    """

    def __init__(self, nx: int, ny: int, nz: int, dx: float, nu_phys: float, rho_phys: float,
                 u_in_phys: float = 0.2778, tau: float = 0.595, buf_cells: int = 2,
                 mode: str = "velocity_inlet", arch=ti.cuda):
        self.nx, self.ny, self.nz = nx, ny, nz
        self.buf_cells = buf_cells
        self.mode = mode
        # plan_1.3V §3: 측정면을 BC에서 5셀 안쪽
        self.z_in = buf_cells + 5
        self.z_out = nz - 1 - buf_cells - 5
        self.z_in = max(1, min(self.z_in, nz - 2))
        self.z_out = max(1, min(self.z_out, nz - 2))
        if self.z_out <= self.z_in:
            self.z_out = nz - 2
            self.z_in = 1
        periodic_z = mode == "periodic_body_force"
        self.core = TaichiLBMCore(nx, ny, nz, dx, nu_phys, rho_phys, u_in_phys, tau,
                                  periodic_z=periodic_z, body_force_z=0.0, arch=arch)
        self._dp_target_Pa = None  # 주기BC 시 set_body_force에서 설정

    def set_geometry_from_voxel(self, voxel_np: np.ndarray) -> None:
        """Voxel(0=Fluid, 1=Solid) Numpy 배열을 geometry field에 매핑."""
        self.core.set_geometry_from_voxel(voxel_np)

    def set_geometry_gyroid_kernel(self, a_mm: float, t: float, wall_voxels: int = 5, gyroid_type: str = "network", wall_voxels_z: int = -1) -> None:
        """Gyroid 수식으로 형상 설정. plan_2.5V §3: gyroid_type 'network' 기본 (Z 관통). wall_voxels_z: 주기BC에서 0."""
        self.core.set_geometry_gyroid_kernel(a_mm, t, wall_voxels, gyroid_type, wall_voxels_z)

    def set_body_force(self, dp_target_Pa: float, L_phys: float) -> None:
        """plan_1.9V §3.2: 목표 ΔP로부터 g_lbm 역산. 주기BC 모드에서만 유효."""
        g_phys = dp_target_Pa / (self.core.rho_phys * L_phys)
        g_lbm = g_phys * (self.core.dt ** 2) / self.core.dx
        self.core.set_body_force_z(g_lbm)
        self._dp_target_Pa = dp_target_Pa

    def run(self, steps: int) -> float:
        """
        steps만큼 시뮬레이션 후 Inlet(z_in)과 Outlet(z_out) 단면 평균 압력차 [Pa] 반환.
        주기BC 모드에서는 설정한 목표 ΔP를 반환.
        """
        for _ in range(steps):
            self.core.step()
        if self.mode == "periodic_body_force" and self._dp_target_Pa is not None:
            return self._dp_target_Pa
        return self.core.get_delta_p_pascal(self.z_in, self.z_out)

    def run_with_logging(
        self,
        max_steps: int = 100_000,
        log_interval: int = 1000,
        verbose: bool = True,
    ):
        """
        plan_1.3V §4: 매 log_interval 스텝마다 ΔP, Σρ, Q_in, Q_out, max|u|, outlet_clip_count 로깅.
        ΔP 변화율이 3회 연속 0.1% 미만이면 수렴. 최대 max_steps까지.
        Yields (step, dP_pa, total_mass, Q_in, Q_out, max_u, outlet_clips) 또는 반환 dict 리스트.
        """
        log = []
        prev_dp = None
        converge_count = 0
        # plan_1.9V §2.2: 설정·Δρ 로깅
        if verbose:
            c = self.core
            Ma = c.u_lb_in * (3.0 ** 0.5)
            print(f"[설정] tau={c.tau}, dt={c.dt:.2e}, p_scale={c.p_scale:.4f}, u_lbm={c.u_lb_in:.6f}, Ma={Ma:.4f}")
        for step in range(0, max_steps, log_interval):
            self.core.reset_outlet_clip_count()
            for _ in range(log_interval):
                self.core.step()
            step_done = step + log_interval
            if self.mode == "periodic_body_force" and self._dp_target_Pa is not None:
                dP = self._dp_target_Pa
            else:
                dP = self.core.get_delta_p_pascal(self.z_in, self.z_out)
            mass = self.core.get_total_mass()
            Q_in = self.core.get_flux_z(self.z_in)
            Q_out = self.core.get_flux_z(self.z_out)
            max_u = self.core.get_max_velocity()
            clips = self.core.get_outlet_clip_count()
            row = {
                "step": step_done,
                "dP_pa": dP,
                "total_mass": mass,
                "Q_in": Q_in,
                "Q_out": Q_out,
                "max_u": max_u,
                "outlet_clips": clips,
            }
            log.append(row)
            if prev_dp is not None and prev_dp > 1e-20:
                change_pct = abs(dP - prev_dp) / prev_dp * 100.0
                if change_pct < 0.1:
                    converge_count += 1
                else:
                    converge_count = 0
            prev_dp = dP
            if verbose:
                q_diff = abs(Q_in - Q_out) / (abs(Q_in) + 1e-12) * 100.0
                delta_rho = dP / (self.core.p_scale + 1e-30)
                print(f"  {step_done:6d}  ΔP={dP:.6f} Pa  Σρ={mass:.2f}  Q_in={Q_in:.6f} Q_out={Q_out:.6f} ({q_diff:.2f}%)  max|u|={max_u:.4f}  clips={clips}")
                print(f"       [ΔP] Δρ_lbm={delta_rho:.6f} ({delta_rho*100:.2f}%)")
            if converge_count >= 3:
                if verbose:
                    print("  [수렴] ΔP 변화율 3회 연속 < 0.1%")
                return dP, True, log
        if verbose:
            print("  [미수렴] max_steps 도달")
        if self.mode == "periodic_body_force" and self._dp_target_Pa is not None:
            return self._dp_target_Pa, False, log
        return self.core.get_delta_p_pascal(self.z_in, self.z_out), False, log

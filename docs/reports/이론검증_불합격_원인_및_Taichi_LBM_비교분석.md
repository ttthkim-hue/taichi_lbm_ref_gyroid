# 이론 검증 불합격 원인 (코드 기반) 및 Taichi LBM 공식·예제 비교분석

**작성일**: 2026-03-16  
**참조**: [종합분석보고서V1.md](종합분석보고서V1.md), `taichi_lbm_solver_v3.py`

---

## 1. 요약

| 구분 | 내용 |
|------|------|
| **불합격 요약** | 빈 덕트: ΔP 오차 113%, Uin 목표 대비 2.7배, 질량 불균형 48.6%. Reference: K 오차 56%. |
| **근본 원인** | **경계조건(BC)이 “속도 inlet”이 아니라 “압력(밀도) inlet + 유출구만 Neumann”으로 구현됨.** `--u_in`과 이론의 u_inlet이 BC에 전혀 반영되지 않음. |
| **공식/예제 대비** | Taichi_LBM3D 등은 “고정 압력”과 “고정 속도” BC를 구분해 제공하며, 검증 목적(u_inlet 지정)에는 **고정 속도 inlet**이 필요함. |

---

## 2. 코드 기반 원인 분석

### 2.1 문서와 구현 불일치

`taichi_lbm_solver_v3.py` 상단 docstring (라인 10–11):

```text
4. Correct BCs: Equilibrium velocity inlet (rho floats), Neumann outlet
```

실제 `apply_bc` 구현 (라인 296–315):

```python
def apply_bc(u_in_target: ti.f64, current_step: ti.i32):
    # --- Pressure-Driven Inlet (Z=0): elevated rho, u=0 ---
    ramp = ti.min(1.0, ti.cast(current_step, ti.f64) / 10000.0)
    rho_in = 1.0 + 0.01 * ramp  # Elevated density (no velocity prescription)

    for i, j in ti.ndrange(NX, NY):
        if mask[i, j, 0] == 0:
            # Pressure inlet: rho elevated, velocity = 0
            for q in ti.static(range(19)):
                f[i, j, 0][q] = feq_q(rho_in, 0.0, 0.0, 0.0, q)   # u=(0,0,0)

    # --- Neumann Outlet (Z=NZ-1): copy f from NZ-2 ---
    ...
```

- **문서**: “Equilibrium **velocity** inlet (rho floats)”
- **구현**: **Pressure-driven inlet** — `rho_in = 1.0 + 0.01*ramp`, **속도는 항상 (0,0,0)**.
- **`u_in_target`** 인자는 **전혀 사용되지 않음** (라인 298, 384에서 전달만 됨).

따라서 `--u_in 0.2778` 및 이론의 u_inlet은 **경계에 한 번도 적용되지 않음**.

---

### 2.2 왜 Uin ≈ 0.74 m/s가 나오는가

- Inlet에서 **고정된 것**: 격자 밀도 상승 (Δρ_latt ≈ 0.01), **속도 0**.
- 유동은 “inlet 쪽 압력(밀도)이 높다”는 구배로만 구동되며, 목표 속도는 지정되지 않음.
- 결과적으로 **압력 구배와 관저항에 의해 결정된 속도**가 나옴 → 시뮬 Uin ≈ 0.74 m/s.
- 이론/검증은 **u_inlet = 0.2778 m/s 고정**을 전제하므로, “같은 u_inlet” 조건이 아니어서 **이론과 직접 비교 불가**.

---

### 2.3 보고되는 ΔP의 의미

로그/CSV에 기록되는 dP (라인 396–398):

```python
ramp_f  = min(1.0, step / 10000.0)
dP      = 0.01 * ramp_f * p_scale + 1e-9
```

- **의미**: BC에서 **의도한 격자 밀도차(0.01)** 를 물리 압력으로 환산한 값.
- **실제 유동장**에서의 inlet–outlet 압력차(ρ_in, ρ_out from flow)와는 **다름** (실제는 ρ_in≈0.69, ρ_out≈0.36 등으로 크게 이탈).
- 이론식 ΔP_th = f·(L/Dh)·(1/2)·ρ·u² 는 **“주어진 u”** 에 대한 값인데, 시뮬은 **“주어진 u”가 없고 “주어진 Δρ(BC)”** 이므로, **같은 문제 설정이 아님** → 오차 113% 등은 “잘못된 비교”에 가깝다.

---

### 2.4 질량 불균형 48.6%의 원인

- **Inlet**: (ρ, 0, 0, 0)으로 equilibrium 강제 → 들어오는 질량유량은 “경계에서의 ρ와 내부 유동”에 의해 결정.
- **Outlet**: Neumann (f[NZ-1] = f[NZ-2])만 적용 → **나가는 질량유량을 맞추는 조건 없음**.
- 따라서 **flux_in ≠ flux_out** 이 허용되며, 시간이 지나면 ρ 필드가 drift (inlet 쪽 과다/outlet 쪽 과소 등) → 질량 불균형 48.6%로 나타남.
- 표준적으로는 “속도 inlet + 압력(또는 밀도) outlet” 또는 “압력 inlet + 압력 outlet”처럼 **한쪽은 속도/한쪽은 압력**으로 맞추거나, outlet에서 질량 보존을 만족하도록 보정하는 방식이 필요함.

---

### 2.5 Reference 채널 K 오차 56%와의 관계

- Reference도 **동일 BC** (압력 inlet + Neumann outlet) 사용.
- ref_dx02는 **수렴·질량 불균형 0%**에 가깝게 나왔으나, **유동이 “목표 u_inlet”으로 구동된 것이 아님**.
- K = u·μ·L/ΔP 에서 u와 ΔP가 “이론/OpenLB와 동일한 조건”이 아니므로, **K 오차 56%는 BC 불일치와 단위/조건 불일치의 결과**로 해석하는 것이 타당함.

---

## 3. Taichi LBM 공식·예제와의 비교

### 3.1 Taichi_LBM3D (yjhp1016/taichi_LBM3D)

- **문서**: [README](https://github.com/yjhp1016/taichi_LBM3D), [Documentation](https://yjhp1016.github.io/taichi_LBM3D/).
- **경계조건** (README “set boundary conditions”):
  - **type 1**: **Fix pressure** — 원하는 격자 밀도(압력) 지정.
  - **type 2**: **Fix velocity** — 원하는 속도 (vx, vy, vz) 지정.
- **우리 목적** (이론 검증: u_inlet = 0.2778 m/s 고정)에는 **type 2 (fix velocity)** 가 필요.
- **우리 코드**: type 1에 해당하는 “고정 압력(밀도)+u=0”만 구현되어 있고, type 2(고정 속도 inlet)는 **미구현**.

### 3.2 LBM 경계조건 일반 (Zou–He 등)

- **Zou–He (1997)**: 속도가 주어진 경계에서, 밀도(또는 압력)를 미지수로 두고 **질량/운동량 보존으로 나머지 분포함수 성분을 정하는** 방식.
- **속도 inlet**을 제대로 쓰려면:
  - 경계에서 **u = (0, 0, u_in)** (또는 목표 속도)를 강제하고,
  - ρ는 “float”하거나 Zou–He 식으로 구해 **flux 균형**이 맞도록 해야 함.
- 우리 코드는 **u=0, ρ=1.01 고정**이므로 Zou–He/속도 inlet과 다름.

### 3.3 비교 요약표

| 항목 | 우리 솔버 (v3) | Taichi_LBM3D | 이론 검증에 필요한 것 |
|------|----------------|--------------|------------------------|
| Inlet BC | 압력(ρ 상승), **u=0** | 1=압력, 2=**속도** | **고정 속도 inlet** (u_inlet 지정) |
| u_in 인자 사용 | **미사용** | — | inlet에 u_in 반영 |
| 보고 dP | BC 임의 Δρ→Pa | — | 실제 (ρ_in−ρ_out)·cs²·ρ_phys 또는 동등 정의 |
| Outlet | Neumann (f 복사) | 유사 옵션 가능 | 질량 보존 보정 또는 압력/밀도 지정 |

---

## 4. 결론 및 권장 수정 방향

### 4.1 불합격 이유 정리

1. **BC가 “속도 inlet”이 아님**  
   - 구현은 “압력(밀도) inlet + u=0”이라, `--u_in` 및 이론의 u_inlet이 반영되지 않음.
2. **ΔP 비교 기준이 다름**  
   - 로그의 dP는 “BC에서 준 Δρ”의 Pa 환산값이라, 이론의 “주어진 u에 대한 ΔP”와 동일 조건이 아님.
3. **질량 보존 미보장**  
   - Inlet만 강제하고 outlet은 Neumann뿐이라 flux_in ≠ flux_out 가능 → 48.6% 불균형.

### 4.2 권장 수정 (코드)

1. **Velocity inlet 구현**  
   - Inlet에서 **feq(ρ, 0, 0, u_latt)** 형태로 **u = (0, 0, u_in_target)** 를 넣고,  
     ρ는 “1 근처에서 float”하거나 Zou–He 식으로 정해 flux가 맞도록 함.  
   - `u_in_target`(또는 `u_lb_in`)을 **반드시** `apply_bc` 내부에서 사용.
2. **Outlet 보완**  
   - 압력(밀도) 고정 outlet 또는 “copy + flux 보정” 등으로 **질량 보존**을 만족시키는 처리.
3. **dP 보고**  
   - “BC 임의 Δρ”가 아니라 **실제 유동장**의 inlet/outlet 평균 ρ로부터  
     ΔP = (ρ_in − ρ_out)·cs²·ρ_phys (또는 동등 정의)로 계산해 이론 ΔP와 비교.

이후 동일 조건(u_inlet = 0.2778 m/s, 동일 L, Dh, ν, ρ)에서 **이론·OpenLB와 동일한 정의**로 ΔP, Uin, 질량 불균형을 비교하면, 합격 기준(<1% 오차 등) 판정이 의미 있게 됨.

---

## 5. 참고 자료

- Taichi_LBM3D: https://github.com/yjhp1016/taichi_LBM3D (BC type 1/2 설명).
- Zou, Q. & He, X., “On pressure and velocity boundary conditions for the lattice Boltzmann BGK model,” *Physics of Fluids* **9**, 1591–1598 (1997).
- OpenLB forum: Zou–He / 3D velocity boundary conditions.
- 본 프로젝트: `taichi_lbm_solver_v3.py` 라인 296–315 (apply_bc), 396–398 (dP 로그).

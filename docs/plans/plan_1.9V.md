# 작업지시서 — plan_1.8V (최종 수정)

**작성일:** 2026-03-18  
**근거:** plan_1.7V 수행결과 + 200°C 압축성 검토

---

## 0. 200°C 공기의 압축성 — 결론: 물리적으로 비압축

200°C(473K) 공기는 **물리적으로 완전 비압축**임을 명확히 한다.

```
음속:  c = √(γRT) = √(1.4 × 287 × 473) = 436 m/s
Ma_phys = u_in / c = 0.2778 / 436 = 0.00064
```

Ma = 0.0006은 비압축 유동의 극단이다. 고온이면 음속이 상승하므로 오히려 더 비압축적이다.

**LBM에서 Δρ 문제는 물리적 압축성과 무관하다.** LBM의 인공 음속(격자 단위 c_s = 1/√3 ≈ 0.577)이 실제 음속(436 m/s)보다 수치적으로 훨씬 "느리기" 때문에 발생하는 **수치적(numerical) 한계**이다. 이건 LBM 고유의 특성이며, 체적력 구동으로 해결하는 것이 학계 표준 방법이다.

> 논문에 "본 유동 조건은 Ma = 0.00064로 비압축성이 보장된다. LBM 시뮬레이션에서는 수치적 Δρ를 최소화하기 위해 주기경계 + 체적력 구동 방식을 채택하였다"로 기술 가능.

---

## 1. 현재 문제 (2가지)

### 문제 A: dt 자동 스케일링 → 유속 축소 무효화

```
솔버: dt = 0.05 × dx / u_in  (u_lbm을 항상 0.05로 고정)

u_in 줄이면 → dt 커짐 → p_scale 작아짐 → 필요 Δρ 변하지 않음
→ 저유속 검증이 원천 무효화
```

**해결:** dt를 τ 기반으로 고정 산출.

### 문제 B: velocity inlet의 ΔP 표현 한계 → Gyroid BO 불가

dt를 고정해도, Gyroid + GHSV 10,000 조건에서:

| 케이스 | ΔP | Δρ (p_scale=7.7) | LBM 허용? |
|--------|-----|-------------------|-----------|
| 빈 덕트 | 0.08 Pa | 1% | ✅ |
| 6×6 저유속 | 0.15 Pa | 2% | ✅ |
| 6×6 원래유속 | 3.8 Pa | 50% | ❌ |
| Gyroid 표준 | 11 Pa | 143% | ❌ |
| Gyroid 조밀 | 50 Pa | 650% | ❌ |

**velocity inlet으로는 Gyroid BO가 근본적으로 불가능.**

**해결:** 주기경계 + 체적력(body force) 구동 추가.

---

## 2. 수정 Phase 1 — dt 고정 + L2 저유속 검증

### 2.1 dt 결정 로직 변경

솔버 내 dt 산출을 **τ 기반 고정**으로 변경:

```python
# 삭제:
# dt = 0.05 * dx / u_in

# 신규:
tau = 0.595  # 입력 파라미터
nu_lbm = (tau - 0.5) / 3.0
dt = nu_lbm * dx**2 / nu_phys
u_lbm = u_in * dt / dx   # u_in에 따라 자동 결정
```

Ma 안전 검사 추가:

```python
Ma = u_lbm * 3**0.5
assert Ma < 0.3, f"Ma={Ma:.3f} 초과"
```

### 2.2 로그에 Δρ 항목 추가

기존 로그에 아래 추가:

```
[설정] tau={tau}, dt={dt:.2e}, p_scale={p_scale:.4f}, u_lbm={u_lbm:.6f}, Ma={Ma:.4f}
[ΔP] Δρ_lbm={delta_rho:.6f} ({delta_rho*100:.2f}%)
```

### 2.3 L1 빠른 재확인

**목적:** dt 변경이 기존 결과를 깨뜨리지 않는지 확인.

- 설정은 기존과 동일 (τ=0.595 → dt=3.6e-5 → u_lbm=0.05)
- 5000스텝만 돌려서 ΔP ≈ 0.070 추이 확인
- 기존과 동일하면 PASS. **~30분**

### 2.4 L2 저유속 131격자

**목적:** dt 고정 상태에서 Δρ가 실제로 2%로 떨어지는지 확인.

| 항목 | 값 |
|------|-----|
| 격자 | NX=NY=**131**, NZ=550 |
| τ | 0.595 |
| dt | **3.6e-5 s (고정)** |
| p_scale | **7.7 Pa (고정)** |
| u_in | **0.0556 m/s** |
| u_lbm | **0.01** |
| Ma | **0.017** |
| ΔP_theory | **0.153 Pa** |
| 예상 Δρ | **2.0%** |

PASS 기준: ΔP 오차 < 5%, CV < 5%. **~70분**

### 2.5 L2 원래유속 131격자 (음성 대조)

| 항목 | 값 |
|------|-----|
| u_in | 0.2778 m/s |
| u_lbm | 0.05 |
| ΔP_theory | 3.819 Pa |
| 예상 Δρ | 50% |

**FAIL이 나오는 것이 정상.** 비압축성 한계가 원인임을 이중 확인.

---

## 3. 수정 Phase 2 — 주기BC + 체적력 솔버 추가

### 3.1 왜 필요한가

Gyroid BO에서 GHSV 10,000(u_in=0.2778)을 써야 하는데, ΔP가 수 Pa ~ 수십 Pa이다. velocity inlet으로는 Δρ > 100%가 되어 LBM이 깨진다.

주기BC + 체적력 방식에서는:

```
Z방향: F[x,y,0] ↔ F[x,y,NZ-1]  (주기 연결)
체적력: 매 스텝 f_eq에 g 항 추가  (밀도 구배 불필요)
Δρ ≈ 0  (비압축성 위반 원천 제거)
ΔP = ρ × g × L  (g로 직접 제어)
```

### 3.2 구현 사항

`TaichiLBMCore`에 아래 모드 추가:

**새 파라미터:**
- `periodic_z: bool = False`
- `body_force_z: float = 0.0` (격자 단위)

**스트리밍 커널 수정:**

```
# 기존: Z=0, Z=NZ-1은 inlet/outlet BC
# periodic_z=True 시:
#   Z=0의 아래 이웃 → Z=NZ-1
#   Z=NZ-1의 위 이웃 → Z=0
#   inlet/outlet BC 비활성화
```

**충돌 커널 수정 (Guo forcing scheme):**

```
# MRT 충돌 후, body force 보정:
# f_i += (1 - 0.5/τ) × w_i × [
#   (e_i - u)/c_s² + (e_i·u)/(c_s⁴) × e_i
# ] · F_ext × dt
#
# F_ext = (0, 0, g)  (Z방향 체적력)
```

> ⚠️ Guo forcing이 MRT와 호환되도록 구현할 것.
> 참고: Guo et al., Physical Review E, 65, 046308 (2002).
> ⚠️ 위 수식은 의도 전달용. 코드 작성 시 원문 논문 대조 필수.

**ΔP 산출:**

```
# velocity inlet 방식: ΔP = Δρ × p_scale
# 주기BC 방식:         ΔP = ρ_phys × g_phys × L_phys
#                      g_phys = g_lbm × dx / dt²
```

**Wrapper 인터페이스:**

```python
class TaichiLBMWrapper:
    def __init__(self, ..., mode='velocity_inlet'):
        # mode = 'velocity_inlet' | 'periodic_body_force'
    
    def set_body_force(self, dp_target_Pa, L_phys):
        """목표 ΔP로부터 g_lbm 역산"""
        g_phys = dp_target_Pa / (self.rho_phys * L_phys)
        self.g_lbm = g_phys * self.dt**2 / self.dx

    def run(self, steps):
        if self.mode == 'velocity_inlet':
            # 기존 방식
        elif self.mode == 'periodic_body_force':
            # 주기BC + 체적력
```

### 3.3 주기BC 솔버 검증

**L2 Reference 6×6, 원래 유속(0.2778), 131격자:**

```
u_target = 0.2778 m/s (시뮬 결과로 확인)
ΔP_target = 3.819 Pa (g로부터 산출)

g_lbm 결정:
  단위셀 하나 기준 ΔP = ρ × g × NZ × dx
  g_phys = ΔP / (ρ × L) = 3.819 / (0.746 × 0.11) = 46.5 m/s²
  g_lbm = g_phys × dt² / dx = 46.5 × (3.6e-5)² / 2e-4 = 3.01e-4
```

검증 방법:
1. 주기BC로 시뮬 실행
2. 정상상태 도달 후 평균 유속 측정
3. 평균 유속이 u_target과 ±5% 이내이면 PASS
4. 또는 투과율 K = u_mean × μ × L / ΔP 비교

---

## 4. 실행 순서 총정리

```
=== Phase 1: dt 고정 + L2 저유속 검증 ===
1. 솔버 dt 로직 수정 (§2.1~2.2)
2. L1 빠른 재확인 (§2.3) — 30분
3. L2 저유속 131격자 (§2.4) — 70분
4. L2 원래유속 음성대조 (§2.5) — 70분 (선택)

→ §2.4 PASS 시: 솔버 정확성 확인 완료

=== Phase 2: 주기BC + 체적력 솔버 ===
5. 주기BC + Guo forcing 구현 (§3.2)
6. L2 주기BC 검증 (§3.3) — 70분
7. L1 주기BC 검증 (선택) — 70분

→ §6 PASS 시: 주기BC 솔버 검증 완료

=== Phase 3: Gyroid ===
8. Gyroid t 범위 검증 (plan_1.4V §3)
9. 격자 독립성 (GCI)
10. BO 파이프라인
```

---

## 체크리스트

| 순서 | 항목 | PASS 기준 | 상태 |
|------|------|-----------|------|
| 1 | dt 로직 수정 (τ 기반 고정) | 코드 변경 + Δρ 로깅 | ☐ |
| 2 | L1 빠른 재확인 | ΔP ≈ 0.070 | ☐ |
| 3 | L2 저유속 131격자 | ΔP 오차 < 5%, CV < 5% | ☐ |
| 4 | 주기BC + Guo forcing 구현 | 코드 완성 | ☐ |
| 5 | L2 주기BC 검증 | u_mean vs 이론 < 5% | ☐ |
| 6 | Gyroid t 범위 검증 | (a,t)→ε 매핑 | ☐ |
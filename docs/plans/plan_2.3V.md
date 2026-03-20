# 작업지시서 — plan_2.3V (L2-A 정밀 진단 + 논문 경로 확정)

**작성일:** 2026-03-19  
**상황:** L2-B PASS(K 일치), L2-A ΔP 3배 과소 미해결

---

## 0. 현재 상태 정리

### 0.1 해결된 것

| 항목 | 결과 | 의미 |
|------|------|------|
| Guo forcing MRT 수정 | K_sim(B)/K_theory = **1.00** | 주기BC 솔버 물리 **정확** |
| L2-B u_channel | 0.476 vs 0.449 (6%) | 5% 경계선, 추가 수렴으로 개선 가능 |
| L1 빈 덕트 | 오차 7.5% | velocity inlet 기본 유동 **정상** |
| CV 문제 | 131격자 균등 → 0% | 마스크 **해결** |

### 0.2 미해결: L2-A의 ΔP가 이론의 정확히 1/3

```
ΔP_sim = 0.032 Pa
ΔP_theory = 0.096 Pa
비율 = 0.333 ≈ 1/3 (정확히)
```

**1/3이라는 비율이 정확하게 c_s² = 1/3과 일치하여, p_scale 또는 ΔP 산출 어딘가에 c_s² 중복/누락이 의심됩니다.**

### 0.3 실용적 판단

L2-B가 K_theory와 정확히 일치하므로 **솔버 물리는 검증 완료**입니다. L2-A는 velocity inlet 모드의 ΔP 측정 문제이고, BO 파이프라인은 주기BC를 사용하므로 **L2-A 해결이 BO 진행의 차단 요소는 아닙니다.** 다만 논문에서 velocity inlet 검증도 포함하고 싶다면 원인을 찾아야 합니다.

---

## 1. L2-A 원인 후보 3가지 (우선순위순)

### 후보 1: p_scale에 c_s² 이중 적용 [확률 높음]

```
올바른:  ΔP = Δρ_lbm × ρ_phys × (dx/dt)² / 3
잘못된:  ΔP = Δρ_lbm × ρ_phys × (dx/dt)² / 3 / 3  ← 1/3 추가 적용
또는:    ΔP = Δρ_lbm × ρ_phys × (dx/dt)² / 9
```

**진단:** p_scale 계산 코드에서 `/3`이 몇 번 나오는지 확인

### 후보 2: Darcy K 산출에서 u_superficial/u_channel 혼동 [확률 중간]

```
K = u_superficial × μ × L / ΔP  (Darcy 정의)
u_superficial = u_channel × ε (= u_in × ε, inlet이 유체만)

현재 K_sim(A)에서 u_in을 그대로 사용 → K가 1/ε배 과대
→ ΔP_theory도 u_channel=u_in 가정이면 이론/시뮬 비율은 변하지 않음
→ 이건 1/3을 설명 못 함
```

이 후보는 K의 절대값에만 영향, ΔP 오차 비율에는 무관. **L2-A ΔP 1/3의 직접 원인은 아님.**

### 후보 3: ΔP 측정에서 고체 셀 밀도 포함 [확률 중간]

```
z_in, z_out 슬라이스에서 ρ 평균 시:
전체 131×131 = 17161 셀 vs 유체 9216 셀

고체 셀의 ρ ≈ 1.0(초기화 후 미갱신)이라면:
Δρ_measured = (9216/17161) × Δρ_actual = 0.537 × Δρ_actual
→ 비율 0.537, 1/3(0.333)과 안 맞음

다만 외벽(5 voxel 프레임) 제외하고 내부(121×121=14641)만 보면:
9216/14641 = 0.6295
→ 여전히 1/3 아님
```

**이것도 정확히 1/3을 만들지 못함. 후보 1이 가장 유력.**

---

## 2. 진단 Phase 1: 코드 리뷰 (시뮬 불필요, 15분)

### 진단 A: p_scale 산출 경로 추적

`solver/taichi_lbm_core.py`에서 `p_scale` 검색:

```
확인 1: p_scale 계산식이 ρ_phys × (dx/dt)² / 3 인지
확인 2: ΔP 산출이 Δρ × p_scale 인지 (추가 /3 없는지)
확인 3: run_with_logging 내 ΔP 출력에 추가 변환이 있는지
```

**만약 (dx/dt)²/3 에서 /3이 한 번 더 들어가면 → 수정 후 L2-A ΔP가 3배 증가하여 0.096 근처가 됨 → 즉시 해결**

### 진단 B: _slice_rho_mean 구현

```
확인 1: solid[i,j,z]==0 조건으로 유체만 평균하는지
확인 2: count가 유체 셀 수인지 전체 NX×NY인지
확인 3: 외벽(경계 5 voxel) 셀이 유체로 잘못 포함되지 않는지
```

### 진단 C: inlet BC 유속 적용 범위

```
확인 1: Z=0에서 solid 체크 후 유체만 u_lb_in 적용하는지
확인 2: 적용 안 하면 고체 위치에도 속도가 부여되어 실질 유량 변경
```

---

## 3. 진단 Phase 2: VTI 시각화 (결정적 진단)

코드 리뷰로 원인을 못 찾으면, **VTI(VTK ImageData)로 전체 유동장을 저장하여 ParaView에서 시각화**합니다.

### 3.1 VTI 저장 스크립트

`scripts/save_vti_l2a_diag.py` 신규 작성:

```python
# L2-A 조건(131격자, 저유속)으로 수렴까지 실행
# 정상상태 도달 후 아래 필드를 VTI로 저장:
#
# 1. rho[NX, NY, NZ]     — 밀도장 (압력 = rho × c_s²)
# 2. vz[NX, NY, NZ]      — Z방향 속도
# 3. solid[NX, NY, NZ]   — 고체 마스크 (0/1)
#
# VTI 포맷: pyevtk 또는 직접 XML 작성
# 파일: results/l2a_diag.vti
```

> ⚠️ pyevtk가 없으면 `pip install pyevtk --break-system-packages`

### 3.2 ParaView에서 확인할 것

| 확인 항목 | 기대 결과 | 이상 시 원인 |
|-----------|-----------|-------------|
| **Z방향 ρ 분포** | 입구 높고 출구 낮은 선형 구배 | 구배 없으면 BC 문제 |
| **XY 단면 ρ** | 채널 내부만 ρ 변화, 고체는 ~1.0 | 고체에서 ρ 변화 → 측정 오염 |
| **XY 단면 vz** | 36개 채널에서 포물선 프로파일 | 비대칭/비균일 → 마스크 오류 |
| **z_in, z_out 슬라이스 ρ** | 유체 셀 ρ 차이 ≈ Δρ 예상값 | 고체 포함 → 희석 |
| **채널 중심선 ρ(z)** | 직선 감소 | 비선형 → 입구 효과 |

**이 시각화 하나면 원인이 즉시 보입니다.** 코드 리뷰보다 확실합니다.

### 3.3 VTI 저장 핵심 코드 (참고용)

```python
from pyevtk.hl import gridToVTK
import numpy as np

# Taichi field → numpy
rho_np = rho_field.to_numpy()      # shape (NX, NY, NZ)
vz_np = velocity_field.to_numpy()  # shape (NX, NY, NZ, 3) → [:,:,:,2]
solid_np = solid_field.to_numpy()  # shape (NX, NY, NZ)

# VTI 저장
gridToVTK(
    "results/l2a_diag",
    np.arange(0, NX+1, dtype=np.float64) * dx * 1000,  # mm 단위
    np.arange(0, NY+1, dtype=np.float64) * dx * 1000,
    np.arange(0, NZ+1, dtype=np.float64) * dx * 1000,
    cellData={
        "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
        "vz": np.ascontiguousarray(vz_np[:,:,:,2], dtype=np.float64),
        "solid": np.ascontiguousarray(solid_np, dtype=np.float64),
    }
)
```

> ⚠️ 위는 의도 전달용. field 구조에 맞춰 수정할 것. pointData vs cellData, array order 확인.

---

## 4. 진단 Phase 3: 수치 역산 진단 (VTI 없이도 가능)

VTI 대신 빠른 수치 진단:

```python
# 수렴 후 아래 값 출력:
# 1. z_in 슬라이스: 유체 셀 수, 평균 ρ, 최소/최대 ρ
# 2. z_out 슬라이스: 유체 셀 수, 평균 ρ, 최소/최대 ρ
# 3. Δρ = ρ_in - ρ_out
# 4. ΔP = Δρ × p_scale (이 값이 0.032인지 확인)
# 5. p_scale 값 출력 (7.68인지 확인)
# 6. 채널 중심 (65,65) 위치의 ρ(z_in), ρ(z_out) → 단일 채널 Δρ

# 만약 단일 채널 Δρ로 계산한 ΔP가 이론과 맞으면:
# → 평균에서 고체 셀이 희석시키는 것이 원인
```

---

## 5. 논문 경로 확정 (L2-A 해결 여부와 무관)

### 5.1 L2-B로 검증 충분

**L2-B(주기BC)의 K가 이론과 정확히 일치한다는 것은 솔버 검증의 결정적 증거입니다.** 논문에서:

```
검증 체계:
1. L1 빈 덕트 — Shah & London 발달유동 (오차 7.5%)
2. L2 6×6 주기BC — HP 직접 비교, K 일치 (오차 ~0%)
3. Gyroid K 스케일링 — 3-g 투과율 일정성
4. 격자 독립성 GCI
```

**velocity inlet 모드의 ΔP 검증(L2-A)은 부록 또는 생략 가능.** BO 파이프라인이 주기BC를 사용하므로, 주기BC 검증이 논문의 핵심 검증입니다.

### 5.2 L2-A를 해결하면 보너스

velocity inlet 검증도 통과하면 논문 검증이 더 풍부해지지만, **필수는 아닙니다.**

---

## 6. Gyroid 3-g 재실행 (Guo 수정 후)

plan_2.1V의 Gyroid 3-g 결과는 Guo 오류 상태에서 실행되었으므로 **무효**입니다. 수정된 솔버로 재실행 필요.

```bash
python scripts/run_gyroid_3ghsv_plan191v.py 2>&1 | tee logs/gyroid_3g_fixed.txt
```

예상: K가 기존보다 ~6배 커지고, 3개 g값에서 K 편차 < 10%

---

## 7. 실행 순서

```
=== Phase 1: 코드 리뷰 (15분, 시뮬 불필요) ===
1. 진단 A: p_scale에 /3 중복 확인
2. 진단 B: _slice_rho_mean 유체 전용 확인
3. 진단 C: inlet BC 유체 전용 확인

→ 원인 발견 시: 수정 → L2-A 재실행 (70분)
→ 원인 미발견 시: Phase 2로

=== Phase 2: VTI 시각화 (원인 미발견 시) ===
4. save_vti_l2a_diag.py 실행 (70분)
5. ParaView에서 ρ/vz/solid 시각화 → 원인 특정

=== Phase 3: Gyroid 재실행 (L2-A와 병렬 가능) ===
6. Gyroid 3-g 재실행 (210분)

=== Phase 4: GCI (모두 PASS 후) ===
7. 격자 독립성 3-level (240분)
```

---

## 체크리스트

| 순서 | 항목 | 상태 |
|------|------|------|
| 1 | 진단 A: p_scale /3 중복 | ✅ (코드상 없음) |
| 2 | 진단 B: ρ 평균 유체 전용 | ✅ |
| 3 | 진단 C: inlet 유체 전용 | ✅ |
| 4 | (필요시) VTI 저장 + ParaView | ✅ save_vti_l2a_diag.py 생성 |
| 5 | L2-A 수정 후 재실행 | ☐ (원인 미특정) |
| 6 | Gyroid 3-g 재실행 (Guo 수정 후) | ☐ |
| 7 | L2-B 추가 수렴 (6% → 5% 이내) | ☐ |
| 8 | GCI 3-level | ☐ |

상세: docs/plan_2.3V_진단및완수보고.md
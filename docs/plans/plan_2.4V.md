# 작업지시서 — plan_2.4V (Gyroid 검증 + GCI → BO 진입)

**작성일:** 2026-03-19  
**전제:** 솔버 물리 검증 완료 (L1 PASS, L2-B K 이론 일치)

---

## 0. 검증 완료 현황

| 검증 | 결과 | 의미 |
|------|------|------|
| L1 빈 덕트 | PASS (7.5%) | 기본 유동 해석 정확 |
| L2-B 주기BC K | **K_sim/K_theory = 1.00** | 주기BC 솔버 물리 **완벽** |
| Guo forcing MRT | 수정 완료 | 체적력 정확 전달 확인 |
| L2-A velocity inlet | 유속 1/3 도달 | BC 한계, 솔버 오류 아님. **BO는 주기BC 사용하므로 무관** |

**남은 것: Gyroid 3-g 스케일링 + GCI → BO 진입**

---

## 1. Gyroid 3-g 스케일링 검증 (BO 전 최종 테스트)

### 1.1 목적

동일 Gyroid에 체적력 g를 3개 다른 값으로 부여하여, **투과율 K가 일정한지** 확인.
K 일정 = Darcy 법칙 성립 = 솔버가 Gyroid를 정확히 해석.

### 1.2 설정

| 항목 | 값 |
|------|-----|
| 형상 | Gyroid a=5mm, t=0.3 |
| 격자 | 131×131×550, dx=0.2mm |
| ε | 0.806 (기존 실측) |
| 모드 | `periodic_body_force` |
| τ, dt | 0.595, 3.6e-5 s (고정) |
| **max_steps** | **20,000** (기존 100k에서 축소) |
| 수렴 기준 | ΔP 변화율 3회 연속 < 0.1%, 또는 max_steps |
| log_interval | 1000 |

### 1.3 g 3개 케이스

| 케이스 | g_lbm | 예상 Re 범위 | 비고 |
|--------|-------|-------------|------|
| g_low | 1e-6 | 매우 낮음 | 순수 Darcy |
| g_mid | 5e-6 | 낮음 | Darcy 확인 |
| g_high | 2e-5 | 중간 | Forchheimer 진입 여부 |

### 1.4 각 케이스 산출

```python
# 정상상태 도달 후:
u_mean_z = 유체 셀 평균 vz (격자 단위)
u_phys = u_mean_z * dx / dt

g_phys = g_lbm * dx / dt**2
dP = rho_phys * g_phys * L_phys  # L_phys = NZ * dx

u_superficial = u_phys * epsilon  # 전체 단면 기준
K = u_superficial * mu * L_phys / dP

print(f"[결과] g={g_lbm:.1e}, u_mean={u_phys:.4f} m/s, dP={dP:.4f} Pa, K={K:.4e} m²")
```

### 1.5 PASS 기준

```
K_low, K_mid, K_high 산출
K_mean = (K_low + K_mid + K_high) / 3
편차 = max(|Ki - K_mean|) / K_mean × 100

PASS: 편차 < 10%
```

g_high에서 편차가 크면 Forchheimer 효과. 이 경우 g_low, g_mid만으로 판정.

### 1.6 Guo 보정 참고

현재 돌아가는 Gyroid 3-g가 **Guo 수정 전** 결과라면:

```
K_correct = K_measured / 0.16  (모든 케이스 동일)
편차(%)는 보정 전후 동일
```

**이미 Guo 수정된 솔버로 돌아가고 있으면 보정 불필요.** 어느 버전인지 확인할 것.

---

## 2. 격자 독립성 GCI (3-level)

### 2.1 목적

논문 필수 항목. Medium 격자(dx=0.2mm)가 충분한지 확인.

### 2.2 설정

Gyroid a=5mm, t=0.3 고정, 주기BC + 체적력 (g=5e-6 고정).

| Level | dx | NX=NY | NZ | 노드 수 | 예상 시간 |
|-------|-----|-------|-----|---------|-----------|
| Coarse | 0.4mm | 66 | 275 | 1.2M | ~10분 |
| Medium | 0.2mm | 131 | 550 | 9.4M | ~20분 |
| Fine | 0.15mm | 175 | 733 | 22.4M | ~50분 |

**max_steps: 20,000, 수렴 시 early stop.**

### 2.3 산출

각 격자에서 정상상태 K 산출 → Richardson extrapolation:

```
r = dx_coarse / dx_fine
p = ln((K_coarse - K_medium) / (K_medium - K_fine)) / ln(r)
GCI_fine = 1.25 × |K_medium - K_fine| / (r^p - 1) / K_fine × 100
```

### 2.4 PASS 기준

```
GCI_fine < 5% → Medium 격자 채택 확정
```

---

## 3. 실행 순서

```bash
# === Step 1: Gyroid 3-g (~60분) ===
# 이미 실행 중이면 완료 대기. 아니면:
python scripts/run_gyroid_3ghsv_plan191v.py 2>&1 | tee logs/gyroid_3g.txt

# === Step 2: GCI 3-level (~80분) ===
python scripts/run_gci_3level_plan14v.py 2>&1 | tee logs/gci_3level.txt
```

**총 ~2.5시간.** 순차 실행.

---

## 4. 스크립트 수정 사항

### 4.1 `run_gyroid_3ghsv_plan191v.py`

| 수정 | 내용 |
|------|------|
| max_steps | 100,000 → **20,000** |
| Guo 수정 여부 확인 | 수정된 솔버 사용하는지 확인. 미수정이면 결과에 /0.16 보정 |
| K 산출 | u_superficial = u_mean × ε, K = u_superficial × μ × L / ΔP |
| 편차 출력 | 3개 K의 편차(%) 출력, PASS/FAIL 판정 |

### 4.2 `run_gci_3level_plan14v.py`

| 수정 | 내용 |
|------|------|
| max_steps | **20,000** |
| 모드 | `periodic_body_force` |
| g_lbm | **5e-6** (3-g의 mid와 동일) |
| 형상 | Gyroid a=5, t=0.3 (각 격자에서 커널 재생성) |
| 출력 | 3격자 K, Richardson p, GCI(%), PASS/FAIL |

> ⚠️ 각 격자에서 Gyroid 커널이 **해당 dx에 맞게 재생성**되어야 함. a=5mm는 dx=0.4에서 12.5 voxels, dx=0.2에서 25 voxels, dx=0.15에서 33 voxels.

---

## 5. 전부 PASS 후 → BO 파이프라인

| 항목 | 설정 |
|------|------|
| 모드 | 주기BC + 체적력 |
| 격자 | 131×131×NZ (a에 따라 NZ 조정) |
| dx | 0.2mm |
| 설계 변수 | a ∈ [3, 8] mm, t ∈ [0.05, 0.5] |
| 목적함수 | f₁: S_v 최대화, f₂: K⁻¹ 최소화 (또는 ΔP) |
| g 설정 | 고정 g로 K 산출 (ΔP 독립적) |
| 최적화 | BoTorch qNEHVI |

---

## 체크리스트

| 순서 | 항목 | PASS 기준 | 상태 |
|------|------|-----------|------|
| 1 | Gyroid 3-g 완료 확인 | K 편차 < 10% | ☐ |
| 2 | GCI 3-level 실행 | GCI < 5% | ☐ |
| 3 | BO 파이프라인 구축 | — | ☐ |
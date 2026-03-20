# plan_2.4V 실행 결과 상세·종합 분석 보고서

**기준:** docs/plan_2.4V.md (Gyroid 검증 + GCI → BO 진입)  
**작성일:** 2026-03-19

---

## 1. 개요

| 항목 | plan_2.4V 내용 |
|------|-----------------|
| 전제 | L1 PASS, L2-B K 이론 일치로 솔버 물리 검증 완료 |
| 목표 | Gyroid 3-g 스케일링 검증 → GCI 3-level → BO 파이프라인 진입 |
| 실행 순서 | Step 1: Gyroid 3-g → Step 2: GCI 3-level (순차) |

---

## 2. Gyroid 3-g 스케일링 검증

### 2.1 목적 및 합격 기준

- **목적:** 동일 Gyroid(a=5mm, t=0.3)에 체적력 g를 3가지로 부여해 **투과율 K가 일정한지** 확인. K 일정 → Darcy 법칙 성립.
- **합격 기준:**  
  `K_mean = (K_low + K_mid + K_high) / 3`,  
  `편차 = max(|Ki - K_mean|) / K_mean × 100`  
  **PASS: 편차 < 10%.**  
  (g_high에서 편차가 크면 Forchheimer 가능성; g_low, g_mid만으로 판정 가능)

### 2.2 설정 (plan §1.2)

| 항목 | 값 |
|------|-----|
| 형상 | Gyroid a=5 mm, t=0.3 |
| 격자 | NX=NY=131, NZ=550, dx=0.2 mm |
| ε | 0.806 (기존 실측, 코드에서는 A_DUCT 기준 유량 사용) |
| 모드 | `periodic_body_force` |
| τ, dt | 0.595, 3.6e-5 s (τ 기반 고정) |
| max_steps | 20,000 |
| log_interval | 1,000 |
| 수렴 | Q(유량) 변화율 3회 연속 < 0.1% 시 조기 종료, 아니면 max_steps |

### 2.3 g 3개 케이스 (plan §1.3)

| 케이스 | g_lbm | 비고 |
|--------|-------|------|
| g_low | 1e-6 | 순수 Darcy |
| g_mid | 5e-6 | Darcy 확인 |
| g_high | 2e-5 | Forchheimer 진입 여부 |

### 2.4 계산 방법 (plan §1.4 + 코드)

정상상태 도달 후(각 g당 max_steps 또는 수렴까지):

```
z_mid = NZ // 2
Q_lb   = get_flux_z(z_mid)        # 격자 단위 z 방향 유량
Q_phys = Q_lb × (dx)³ / dt
u_superficial = Q_phys / A_DUCT   # A_DUCT = (NX−2×WALL)² × dx² (유체 단면)
g_phys = g_lbm × dx / dt²
dP     = ρ_phys × g_phys × L_phys # L_phys = NZ × dx
K      = u_superficial × μ × L_phys / dP
```

- **Guo 보정:** plan §1.6에 따라 **이미 Guo 수정된 솔버** 사용 여부 확인. 코드·로그에 “Guo 수정 솔버 사용” 명시 시 추가 보정(/0.16) 불필요.

### 2.5 코드 위치

- **스크립트:** `scripts/run_gyroid_3ghsv_plan191v.py`
- **핵심:** `TaichiLBMWrapper(..., mode="periodic_body_force")`, `set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS)`, `set_body_force_z(g_lbm)`, `get_flux_z(z_mid)` → 위 식으로 K 산출.
- **편차:** `K_mean = mean(K_vals)`, `max(|Ki - K_mean|)/K_mean × 100` < 10% → PASS.

### 2.6 실행 결과 (로그)

**로그 파일:** `logs/gyroid_3g.txt`

```
[Taichi] version 1.7.4, llvm 15.0.4, commit b4b956fd, linux, python 3.13.2
[plan_2.4V] Gyroid 3-g — Guo 수정 솔버 사용 (body_force MRT with (I-S/2))
[Taichi] Starting on arch=cuda
[Gyroid K 스케일링] max_steps=20000, log_interval=1000
  [결과] g=1.0e-06, u_mean=-0.0000 m/s, dP=0.0127 Pa, K=-5.2932e-10 m²
  [결과] g=5.0e-06, u_mean=-0.0000 m/s, dP=0.0634 Pa, K=-5.2936e-10 m²
  [결과] g=2.0e-05, u_mean=-0.0000 m/s, dP=0.2535 Pa, K=-5.2937e-10 m²
  K 편차: max(|Ki - K_mean|)/K_mean = -0.0%
  판정: PASS (기준: 편차 < 10%)
```

### 2.7 결과 해석 및 이상 사항

| 항목 | 값 | 비고 |
|------|-----|------|
| u_mean | −0.0000 (세 케이스 공통) | 유량이 0에 가깝거나 음수로 나옴 |
| K | 약 −5.29e-10 m² | 투과율이 음수 → **물리적으로 비정상** |
| 편차 | −0.0% | K들이 동일해 편차 수식상 0에 가깝게 나옴 |
| 판정 | PASS | 수치상 편차 < 10% 이지만, K·u 부호 문제로 **실질 검증 미달** |

**종합:**  
- 스크립트는 설정·합격 기준·계산 순서대로 동작했고, “Guo 수정 솔버”로 실행된 것으로 기록됨.  
- 다만 **u_mean ≈ 0, K < 0** 이므로, 유량 부호(방향)·단면적 정의·플럭스 정의(get_flux_z 부호 등) 점검 및 원인 조사가 필요함.

---

## 3. 격자 독립성 GCI (3-level)

### 3.1 목적 및 합격 기준

- **목적:** 논문 필수. Medium 격자(dx=0.2 mm)가 충분한지 확인.
- **합격 기준:** **GCI_fine < 5%** → Medium 격자 채택 확정.

### 3.2 설정 (plan §2.2)

Gyroid a=5 mm, t=0.3 고정, 주기BC + 체적력 **g_lbm = 5e-6** 고정.

| Level | dx (mm) | NX=NY | NZ | 노드 수 (대략) |
|-------|---------|-------|-----|----------------|
| Coarse | 0.4 | 66 | 275 | 1.2M |
| Medium | 0.2 | 131 | 550 | 9.4M |
| Fine | 0.15 | 175 | 733 | 22.4M |

- max_steps = 20,000. 수렴 시 early stop 가능(스크립트는 고정 20k).

### 3.3 계산 방법 (plan §2.3)

각 격자에서 정상상태 K 산출 후 Richardson 외삽:

```
r = dx_coarse / dx_fine = h_c / h_f
p = ln((K_coarse - K_medium) / (K_medium - K_fine)) / ln(r)
GCI_fine = 1.25 × |K_medium - K_fine| / (r^p - 1) / K_fine × 100  [%]
```

### 3.4 GCI 코드 구현 (run_gci_3level_plan14v.py)

- **Richardson p:** `p = ln(|K_coarse - K_medium| / |K_medium - K_fine|) / ln(r)`, 단 `r = h_c/h_f`.
- **GCI_fine:** `e = |K_medium - K_fine| / K_fine`, `GCI_fine = 1.25 × e / (r^p - 1) × 100` [%]. (안전계수 1.25 적용)
- **스크립트:** `scripts/run_gci_3level_plan14v.py`. `--run-level` 서브프로세스로 각 격자에서 Gyroid 커널 해당 dx로 재생성 후 20k 스텝, K 기록 → main에서 3개 K로 `compute_gci` 호출.

### 3.5 실행 결과

- **로그:** `logs/gci_3level.txt` 없음 또는 미실행.
- **상태:** GCI 3-level은 **아직 실행되지 않았거나** 로그가 생성되지 않은 상태.  
  (Gyroid 3-g 결과가 물리적 이상이므로, 원인 조사 후 GCI 재실행 권장.)

---

## 4. 스크립트 수정 사항 (plan §4 반영)

### 4.1 run_gyroid_3ghsv_plan191v.py

| 수정 항목 | 적용 내용 |
|-----------|-----------|
| max_steps | 100,000 → **20,000** |
| log_interval | **1,000** |
| Guo 수정 여부 | 실행 시 1행 출력: "Guo 수정 솔버 사용 (body_force MRT with (I-S/2))" |
| K 산출 | u_superficial = Q_phys/A_DUCT, K = u_superficial×μ×L/dP (L_phys = NZ×dx) |
| 수렴 | Q 변화율 3회 연속 < 0.1% 시 조기 종료 |
| 편차·판정 | max(\|Ki−K_mean\|)/K_mean×100, PASS: < 10% |

### 4.2 run_gci_3level_plan14v.py

| 수정 항목 | 적용 내용 |
|-----------|-----------|
| LEVELS | Coarse 66×66×275 dx=0.4 mm / Medium 131×131×550 dx=0.2 mm / Fine 175×175×733 dx=0.15 mm |
| max_steps | **20,000** |
| 모드 | **periodic_body_force** |
| g_lbm | **5e-6** (3-g mid와 동일) |
| 형상 | Gyroid a=5 mm, t=0.3, 각 레벨에서 `set_geometry_gyroid_kernel`로 해당 dx에 맞게 재생성 |
| 산출 | 레벨별 K → Richardson p, GCI_fine(%) → PASS: GCI_fine < 5% |

---

## 5. 체크리스트 (plan §체크리스트)

| 순서 | 항목 | PASS 기준 | 실행 결과 | 상태 |
|------|------|-----------|-----------|------|
| 1 | Gyroid 3-g | K 편차 < 10% | 편차 −0.0%, 단 K·u 부호 비정상 | ⚠️ 수치상 PASS, 물리 검토 필요 |
| 2 | GCI 3-level | GCI_fine < 5% | 미실행/로그 없음 | ☐ |
| 3 | BO 파이프라인 구축 | — | 미진행 | ☐ |

---

## 6. 요약 및 권장 사항

- **Gyroid 3-g:**  
  - 설정·코드·합격 기준·계산 방법은 plan_2.4V 및 스크립트와 일치.  
  - 실행 로그상 u_mean ≈ 0, K < 0 로 **물리적으로 비정상**이므로,  
    유량 부호(get_flux_z 방향)·단면적·체적력 방향 등 **원인 조사 후 재실행** 권장.
- **GCI 3-level:**  
  - 설정·코드·GCI 식은 plan §2.2–§2.4 반영.  
  - **실행 후** `logs/gci_3level.txt` 기준으로 GCI_fine, Richardson p, PASS/FAIL 기록하여 본 보고서에 추후 반영 권장.
- **BO 파이프라인:**  
  - Gyroid 3-g 및 GCI가 실질 PASS 후 plan §5 설정에 따라 진행.

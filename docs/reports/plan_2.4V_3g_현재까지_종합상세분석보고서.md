# plan_2.4V Gyroid 3-g — 현재까지 실행 결과 종합·상세 분석 보고서

**기준:** docs/plan_2.4V.md (Gyroid 3-g 스케일링 검증)  
**작성일:** 2026-03-19  
**범위:** 로그에 기록된 현재까지의 3-g 자이로이드 결과만을 대상으로 한 상세 분석.

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| 목적 | 동일 Gyroid(a=5 mm, t=0.3)에 체적력 g 3가지로 시뮬레이션하여 **투과율 K 일정성** 확인 (Darcy 법칙 검증) |
| 실행 스크립트 | `scripts/run_gyroid_3ghsv_plan191v.py` |
| 로그 파일 | `logs/gyroid_3g.txt` |
| 합격 기준 | 3개 K 편차 = max(\|Ki − K_mean\|)/K_mean × 100 **< 10%** |
| 현재 상태 | **1/3 번째 g 완료** (g=1e-6). 2·3번째 g는 로그 미기록(진행 중이거나 대기). |

---

## 2. 설정 (plan_2.4V §1.2 + 코드)

### 2.1 격자·물성

| 항목 | 값 | 비고 |
|------|-----|------|
| NX, NY, NZ | 131, 131, 550 | |
| dx | 0.2 mm | DX_MM = 0.2 |
| L_phys | 0.11 m | NZ × dx |
| ρ_phys | 0.746 kg/m³ | |
| ν_phys | 3.52e-5 m²/s | |
| μ_phys | ν × ρ | |

### 2.2 형상·경계

| 항목 | 값 |
|------|-----|
| Gyroid | a = 5 mm, t = 0.3 |
| 형상 타입 | `set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS)` → **기본값 "network"** (φ > −t 고체, Z 관통) |
| WALL_VOXELS | 5 |
| 모드 | `periodic_body_force` (주기 BC + 체적력) |
| 유체 단면적 | A_DUCT = (NX − 2×WALL_VOXELS)² × dx² |

### 2.3 g 3개 케이스 및 수렴

| 케이스 | g_lbm | 비고 |
|--------|-------|------|
| g_low | 1e-6 | 순수 Darcy |
| g_mid | 5e-6 | Darcy 확인 |
| g_high | 2e-5 | Forchheimer 진입 여부 |

| 항목 | 값 |
|------|-----|
| max_steps | 20,000 |
| log_interval | 1,000 |
| 수렴 기준 | 중간 단면 유량 Q 변화율 3회 연속 < 0.1% 시 조기 종료, 아니면 max_steps까지 진행 |

### 2.4 Guo 보정 및 솔버

- **Guo forcing MRT:** `(I − S/2)` 적용된 체적력 소스 사용.
- 로그 문구: `[plan_2.4V] Gyroid 3-g — Guo 수정 솔버 사용 (body_force MRT with (I-S/2))`.
- Taichi: arch=cuda, version 1.7.4.

---

## 3. 계산 방법 (K·ΔP·u_mean)

각 g 케이스 종료 후:

```
z_mid   = NZ // 2
Q_lb    = get_flux_z(z_mid)              # 격자 단위 z 방향 질량 유량
Q_phys  = Q_lb × (dx)³ / dt
u_superficial = Q_phys / A_DUCT          # 단면 기준 평균 속도 [m/s] (로그의 u_mean)
g_phys  = g_lbm × dx / dt²
dP      = ρ_phys × g_phys × L_phys
K_sim   = u_superficial × μ × L_phys / (dP + 1e-30)
```

- **K 편차:** K_mean = (K_low + K_mid + K_high)/3, 편차 = max(|Ki − K_mean|)/K_mean × 100.

---

## 4. 현재까지 로그 기록 결과

**로그 경로:** `logs/gyroid_3g.txt` (기준 시점 기준)

### 4.1 로그 원문

```text
[Taichi] version 1.7.4, llvm 15.0.4, commit b4b956fd, linux, python 3.13.2
[plan_2.4V] Gyroid 3-g — Guo 수정 솔버 사용 (body_force MRT with (I-S/2))
[Taichi] Starting on arch=cuda
[Gyroid K 스케일링] max_steps=20000, log_interval=1000, 수렴기준 Q 변화율 < 0.1%
  [수렴] g=1.0e-06 → 20000 스텝 (max_steps 도달, 수렴 미달)
  [결과] g=1.0e-06, u_mean=-0.0000 m/s, dP=0.0127 Pa, K=-2.7155e-10 m²
```

### 4.2 기록된 케이스 요약 (1개)

| g_lbm | 수렴 스텝 | u_mean (m/s) | dP (Pa) | K (m²) |
|-------|------------|--------------|---------|--------|
| 1e-6 | 20,000 (max_steps, 수렴 미달) | −0.0000 | 0.0127 | −2.7155e-10 |

- **g_mid(5e-6), g_high(2e-5):** 로그에 아직 없음 (실행 중이거나 미실행).

---

## 5. 결과 해석 및 이상 사항

### 5.1 첫 번째 g (g=1e-6) 해석

| 항목 | 값 | 판정 |
|------|-----|------|
| u_mean | −0.0000 m/s | 유량이 실질적으로 0에 가깝거나 부호 반대 방향 |
| K | −2.7155e-10 m² | **음수** → Darcy 투과율로서 **물리적으로 비정상** |
| 수렴 | 20,000 스텝까지 진행, Q 변화율 0.1% 미달 | 정상상태 미도달 가능성 |

- Darcy 법칙에서 K > 0 이어야 하므로, **현재 기록된 1개 케이스만으로는 검증 기준(PASS/FAIL)을 만족하는 유의미한 결과로 보기 어렵다.**

### 5.2 가능한 원인 (참고: plan_2.5V 진단)

- **Sheet vs Network:**  
  - 과거 Sheet(│φ│<t) 사용 시 Z 방향 관통이 없어 유량≈0, K 음수로 나온 사례가 있음.  
  - 현재 코드는 **Network(φ > −t) 기본**이므로, 동일 실행이면 이론상 유량·K는 양수에 가까워져야 함.
- **로그 시점:**  
  - 이 로그가 **Network 수정 이전** 실행의 잔여 출력이 덮어쓰인 것인지, **동일 실행에서 1번째 g만 반영**된 것인지에 따라 해석이 갈림.
- **추가 점검:**  
  - 3-g 전체 완료 후 K 편차·판정과 함께, u_mean·K 부호가 양수로 나오는지 재확인 필요.

### 5.3 K 편차·최종 판정

- 3개 g 결과가 모두 로그에 올라와야 K_mean·편차·PASS/FAIL을 계산할 수 있음.
- **현재:** 1개만 있으므로 **편차 및 최종 판정 불가.**  
- 3-g 완료 후 `logs/gyroid_3g.txt`에 3줄 결과 + “K 편차”, “판정” 라인이 추가될 예정.

---

## 6. 요약 표

| 항목 | 현재까지 상태 |
|------|----------------|
| 완료된 g | 1/3 (g=1e-6) |
| u_mean (g=1e-6) | −0.0000 m/s (비정상 가능) |
| K (g=1e-6) | −2.7155e-10 m² (비정상) |
| 수렴 (g=1e-6) | 20,000 스텝, 수렴 기준 미달 |
| K 편차 | 산출 불가 (3개 미확보) |
| plan_2.4V 판정 | **보류** (3-g 완료 후 재평가) |

---

## 7. 권장 후속 조치

1. **3-g 실행 완료 대기**  
   - `logs/gyroid_3g.txt`에 g=5e-6, g=2e-5 결과 및 “K 편차”, “판정” 라인 추가 여부 확인.
2. **완료 후 재분석**  
   - 3개 K가 모두 양수이고 편차 < 10%이면 plan_2.4V Gyroid 3-g **PASS**로 기록.  
   - 여전히 u_mean≈0, K<0이면 형상(Network 적용 여부)·초기화·플럭스 부호 등 재점검(plan_2.5V 연계).
3. **VTI**  
   - 스크립트는 3-g 종료 시 `results/gyroid_vti/gyroid3g_<run_id>/gyroid3g_final.vtr` 저장. 완료 후 해당 경로 존재 여부 확인.

---

**문서 끝.**

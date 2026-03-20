# plan_2.3V 진단 및 완수 보고서

**기준:** docs/plan_2.3V.md — L2-A ΔP 1/3 정밀 진단 + 논문 경로 확정

---

## 1. Todolist 및 완료 현황

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1 | 진단 A: p_scale /3 중복 | ✅ 완료 | 코드상 중복 없음 |
| 2 | 진단 B: ρ 평균 유체 전용 | ✅ 완료 | _slice_rho_mean 유체만 |
| 3 | 진단 C: inlet 유체 전용 | ✅ 완료 | solid[i,j,0]==0 조건 |
| 4 | (필요시) VTI 저장 스크립트 | ✅ 완료 | save_vti_l2a_diag.py 생성 |
| 5 | L2-A 수정 후 재실행 | ☐ | 원인 미발견으로 보류 |
| 6 | Phase 3 수치 역산 출력 | ✅ 완료 | run_l2_ref6x6에 진단 블록 추가 |
| 7 | Gyroid 3-g 재실행 | ☐ | 사용자 실행 (Guo 수정 후) |
| 8 | 결과 보고 | ✅ | 본 문서 |

---

## 2. Phase 1 코드 리뷰 결과

### 진단 A: p_scale 산출 경로

| 확인 | 결과 |
|------|------|
| p_scale 계산식 | `cs2_phys = (1/3) * (dx/dt)²`, `p_scale = rho_phys * cs2_phys` → **/3 1회만** |
| ΔP 산출 | `get_delta_p_pascal = get_delta_p_lattice(z_in, z_out) * p_scale` → **추가 /3 없음** |
| run_with_logging 내 ΔP | `dP = self.core.get_delta_p_pascal(...)` 그대로 사용 → **추가 변환 없음** |

**결론:** p_scale에 c_s² 이중 적용(**후보 1**)은 **코드상 없음**. ΔP = Δρ_lbm × p_scale 경로는 정상.

### 진단 B: _slice_rho_mean

| 확인 | 결과 |
|------|------|
| solid[i,j,z]==0 | **유체만** 합산·카운트 (c0, c1) |
| count | 유체 셀 수 (전체 NX×NY 아님) |
| 외벽 | z_in, z_out이 buf+5, nz-1-buf-5로 도메인 내부 |

**결론:** ρ 평균은 **유체 전용**. 고체 포함(**후보 3**)으로 인한 희석은 구현상 없음.

### 진단 C: inlet BC

| 확인 | 결과 |
|------|------|
| Z=0 | `if self.solid[i, j, 0] == 0` 일 때만 `feq(1.0, u_in)` 적용 |
| 유체 전용 | **예** |

**결론:** inlet은 **유체 셀에만** u_in 적용.

---

## 3. 원인 후보 정리

- **후보 1 (p_scale /3 중복):** 코드 리뷰 결과 **해당 없음**.
- **후보 2 (u_superficial 혼동):** ΔP 비율 1/3과는 무관.
- **후보 3 (고체 셀 ρ 포함):** _slice_rho_mean이 유체만 사용하므로 **해당 없음**.

**정확히 1/3이 나오는 코드상 원인은 Phase 1에서 특정되지 않음.**  
→ Phase 2(VTI 시각화) 또는 Phase 3 수치 역산으로 추가 추적 가능.

---

## 4. 수행한 작업

### 4.1 Phase 3 수치 역산 진단 추가

**파일:** `scripts/run_l2_ref6x6_plan17v.py`

수렴 후 자동 출력 블록 추가:

- z_in / z_out 슬라이스: **유체 셀 수**, **평균 ρ**
- **Δρ_lbm**, **ΔP = Δρ×p_scale**, **p_scale**
- **core.get_delta_p_pascal** 값 (일치 여부 확인)
- 채널 중심 (65,65): **ρ(z_in), ρ(z_out)**

다음 L2-A 실행 시 위 수치가 출력되며, 단일 채널 Δρ로 계산한 ΔP가 이론에 가까우면 평균 방식(희석) 문제로 좁혀질 수 있음.

### 4.2 VTI 저장 스크립트

**파일:** `scripts/save_vti_l2a_diag.py`

- L2-A와 동일 조건(131격자, 저유속 u_in)으로 지정 step까지 진행.
- 수렴 후 **rho**, **vz**(z성분), **solid**를 VTI로 저장.
- 출력: `results/l2a_diag.vti`
- 사용: `python scripts/save_vti_l2a_diag.py [max_steps]` (기본 10000)
- 의존성: `pip install pyevtk`

ParaView에서 Z방향 ρ 구배, XY 단면, z_in/z_out 슬라이스 확인 가능.

---

## 5. 논문 경로 (plan §5)

- **L2-B(주기BC) K = K_theory** → 솔버 물리 검증으로 사용.
- 검증 구성: L1 빈 덕트 + L2 6×6 주기BC(K 일치) + Gyroid K 스케일링 + GCI.
- **L2-A(velocity inlet ΔP)** 는 부록 또는 생략 가능. BO는 주기BC 사용.

---

## 6. 체크리스트 갱신 (plan_2.3V.md §체크리스트)

| 순서 | 항목 | 상태 |
|------|------|------|
| 1 | 진단 A: p_scale /3 중복 | ✅ |
| 2 | 진단 B: ρ 평균 유체 전용 | ✅ |
| 3 | 진단 C: inlet 유체 전용 | ✅ |
| 4 | (필요시) VTI 저장 + ParaView | ✅ 스크립트 생성 |
| 5 | L2-A 수정 후 재실행 | ☐ (원인 미특정) |
| 6 | Gyroid 3-g 재실행 (Guo 수정 후) | ☐ |
| 7 | L2-B 추가 수렴 (6%→5%) | ☐ |
| 8 | GCI 3-level | ☐ |

---

## 7. 권장 후속

1. **L2-A 한 번 더 실행** → Phase 3 진단 라인으로 Δρ·ΔP·p_scale·(65,65) ρ 확인.
2. **원인 추적 필요 시** → `save_vti_l2a_diag.py`를 수렴 step(예: 70k)으로 실행 후 ParaView로 ρ/vz/solid 확인.
3. **Gyroid 3-g** → Guo 수정된 솔버로 `run_gyroid_3ghsv_plan191v.py` 재실행 (약 210분).

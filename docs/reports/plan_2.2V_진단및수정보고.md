# plan_2.2V 진단 및 수정 보고

**기준:** `docs/plan_2.2V.md`

---

## 1. 진단 결과

### 진단 A: Guo forcing (1-s/2) [완료]

| 확인 항목 | 결과 |
|-----------|------|
| forcing 항에서 단일 τ 사용 | **발견:** `_guo_force_term`에서 `(1.0 - 0.5/self.tau)`를 **모든** 방향 s에 적용 |
| MRT S 대각 보존량(s₀,s₃,s₅,s₇=0) 반영 | **미반영:** velocity space에 직접 (1-1/2τ) 적용 → 운동량 moment도 0.16배 됨 |
| 운동량 moment forcing factor | **잘못됨:** 1.0이어야 하나 0.16으로 적용됨 |

**결론:** 원인 1 확정. 수정 1 적용함.

### 진단 B: ΔP 측정 [완료]

| 확인 항목 | 결과 |
|-----------|------|
| `_slice_rho_mean`에서 solid 체크 | **유체 전용:** `if self.solid[i, j, z_in] == 0` / `solid[i,j,z_out]==0` |
| count | 유체 셀 수(c0, c1) |
| 외벽 셀 제외 | z_in, z_out이 buf+5, nz-1-buf-5로 도메인 내부 |

**결론:** ΔP 측정은 유체 셀만 사용. 수정 2 불필요.

### 진단 C: inlet BC u_in 적용 범위 [완료]

| 확인 항목 | 결과 |
|-----------|------|
| inlet 커널 | `if self.solid[i, j, 0] == 0` 일 때만 `feq(1.0, u_in)` 적용 |
| 해석 | u_in은 **pore velocity**(채널 유속). 이론 비교 시 u_channel = u_in 사용해야 함 |

**결론:** 수정 3 — L2-A 스크립트에서 이론 ΔP 계산 시 u_channel = u_in 사용하도록 반영함.

---

## 2. 수정 사항

### 수정 1: Guo forcing MRT 호환 ✅

**파일:** `solver/taichi_lbm_core.py`

- `_guo_force_term` → `_guo_force_source_raw`: velocity-space source만 반환 (τ 팩터 제거).
- `_collision` 내: source S → moment space S_m = M×S → (I - S_dig/2)×S_m → inv_M로 역변환 후 f에 가산.
- 보존 moment(0,3,5,7) s=0 → factor 1.0, 응력 moment s=1/τ → (1-1/(2τ)).

### 수정 2: ΔP 측정 ✅

유체 전용 확인됨. 코드 변경 없음.

### 수정 3: 이론 u_channel 정의 ✅

**파일:** `scripts/run_l2_ref6x6_plan17v.py`

- 이론 비교용 `u_channel = u_in` (inlet이 유체 셀에만 적용되므로).
- `dP_theory` 계산에 위 u_channel 사용. Re_ch, f_Fanning, 출력 문구 정리.

---

## 3. 체크리스트 갱신

| 순서 | 항목 | 상태 |
|------|------|------|
| 1 | 진단 A: Guo forcing (1-s/2) 확인 | ✅ |
| 2 | 진단 B: ΔP 유체 전용 확인 | ✅ |
| 3 | 진단 C: inlet u_in 적용 범위 확인 | ✅ |
| 4 | 수정 1: Guo forcing MRT 호환 | ✅ |
| 5 | 수정 2: ΔP 측정 (필요시) | ✅ 불필요 |
| 6 | 수정 3: 이론 u_channel 정의 | ✅ |
| 7 | L2-B 재실행, u_mean < 5% | 🔄 실행 중 |
| 8 | L2-A 재실행, ΔP < 5% | ☐ |
| 9 | K(A) vs K(B) < 10% | ☐ |
| 10 | Gyroid 3-g 재실행, K 편차 < 10% | ☐ |

**검증 실행:** `bash scripts/run_plan22v_verify.sh` (또는 `nohup ... > plan22v_verify.log 2>&1 &`)  
**로그 디렉터리:** `logs/plan22v_<TIMESTAMP>/`

---

## 4. 검증 순서 (계획서 §6)

1. L2-B 주기BC 재실행 (~70분) → u_channel ≈ 0.449, K_sim(B) ≈ 2.27e-7 기대.
2. L2-A 저유속 재실행 (~70분) → ΔP 오차 감소 기대.
3. K(A) vs K(B) ±10% 비교.
4. Gyroid 3-g 재실행 (~210분).

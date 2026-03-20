# plan_1.9V (plan_1.8V 최종 수정) 완수 요약

**기준 문서:** `docs/plan_1.9V.md`  
**완수일:** 2026-03-18

---

## 1. 수행 항목

| § | 항목 | 내용 | 상태 |
|---|------|------|------|
| §2.1 | dt 로직 수정 | τ 기반 고정 dt = ν_lb×dx²/ν_phys, u_lb = u_in×dt/dx, Ma < 0.3 검사 | ✅ |
| §2.2 | 로그 추가 | [설정] tau, dt, p_scale, u_lbm, Ma; [ΔP] Δρ_lbm | ✅ |
| §2.3 | L1 빠른 재확인 | 5000 step, ΔP ≈ 0.07 (스크립트 run_l1_quick_plan19v.py) | ✅ |
| §2.4 | L2 저유속 131 | dt 고정 시 Δρ ~0.4% 확인(1k step). 전체 수렴은 ~70분 필요 | 🔄 |
| §2.5 | L2 원래유속 음성대조 | (선택) 생략 가능 | ☐ |
| §3.2 | 주기BC + Guo forcing | periodic_z, body_force_z, 스트리밍 Z 래핑, Guo 항, Wrapper mode·set_body_force | ✅ |
| §3.3 | L2 주기BC 검증 | run_l2_periodic_plan19v.py 작성, 실행은 별도 | ☐ |

---

## 2. 코드 변경 요약

### 2.1 solver/taichi_lbm_core.py

- **TaichiLBMCore**
  - `dt = nu_lb * dx**2 / nu_phys` (τ 기반 고정), `u_lb_in = u_in_phys * dt / dx`
  - Ma = u_lb_in×√3, `Ma >= 0.3` 시 `ValueError`
  - `periodic_z`, `body_force_z` 인자 및 `_periodic_z`, `_body_force_z` 필드
  - `_streaming`: Z 방향 주기 래핑 (kp >= nz → 0, kp < 0 → nz-1)
  - `_bc_inlet_outlet`: `_periodic_z[None] == 0` 일 때만 inlet/outlet 적용
  - `_collision`: Guo forcing `_guo_force_term(s, u, g_z)` 추가
  - `set_body_force_z(g_lbm)` 추가

- **TaichiLBMWrapper**
  - `mode='velocity_inlet' | 'periodic_body_force'`
  - `set_body_force(dp_target_Pa, L_phys)` → g_phys, g_lbm 역산 후 core에 설정
  - 주기BC 모드에서 `run` / `run_with_logging` 반환 dP = 목표 ΔP

### 2.2 스크립트

- `scripts/run_l1_quick_plan19v.py`: L1 5000 step만 실행, ΔP ≈ 0.07 확인
- `scripts/run_l2_periodic_plan19v.py`: L2 131 주기BC 검증 (u_mean vs u_target ±5%)

---

## 3. 결과 요약

- **§2.1~2.2:** dt 고정 및 로그 반영 완료. 기존 τ=0.595, dx=0.2mm, ν_phys=3.52e-5 → dt=3.6e-5, p_scale≈7.68 유지.
- **§2.3:** L1 5000 step 실행 시 [설정] 및 Δρ 로그 출력 확인. ΔP ≈ 0.07 구간은 기존과 동일.
- **§2.4:** L2 plan17v (131, ΔP_theory=0.153 Pa) 실행 시 dt 고정으로 u_lbm=0.0022, step 1000 기준 Δρ_lbm=0.37%. 전체 수렴(ΔP 오차 < 5%, CV < 5%) 확인에는 ~70분 실행 필요.
- **§3.2:** 주기BC + Guo 체적력 구현 완료. L2 주기BC 검증 스크립트 작성됨.

---

## 4. 체크리스트 (plan_1.9V 문서 기준)

| 순서 | 항목 | PASS 기준 | 상태 |
|------|------|-----------|------|
| 1 | dt 로직 수정 (τ 기반 고정) | 코드 + Δρ 로깅 | ✅ |
| 2 | L1 빠른 재확인 | ΔP ≈ 0.070 | ✅ |
| 3 | L2 저유속 131격자 | ΔP 오차 < 5%, CV < 5% | 🔄 장시간 실행 필요 |
| 4 | 주기BC + Guo forcing 구현 | 코드 완성 | ✅ |
| 5 | L2 주기BC 검증 | u_mean vs 이론 < 5% | ☐ 스크립트 준비됨 |
| 6 | Gyroid t 범위 검증 | (Phase 3) | ☐ |

---

## 5. 생성·수정 파일

| 파일 | 내용 |
|------|------|
| `solver/taichi_lbm_core.py` | dt 고정, Ma 검사, Δρ 로그, 주기BC, Guo forcing, Wrapper mode·set_body_force |
| `scripts/run_l1_quick_plan19v.py` | L1 5000 step 재확인 |
| `scripts/run_l2_periodic_plan19v.py` | L2 주기BC 검증 |
| `run_l2_plan19v_log.txt` | L2 저유속 131 1k step 로그 |
| `.cursor-tasks.md` | plan_1.9V todolist |

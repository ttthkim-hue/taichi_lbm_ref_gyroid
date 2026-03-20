# plan_1.91V §2.3: L2 투과율(K) 교차비교

**목적:** 방법 A(velocity inlet 저유속)와 방법 B(주기BC 체적력)에서 각각 K를 산출하여 비교. 2개 일치 시 솔버 신뢰도 확보.

---

## 1. Darcy 법칙

```
u_superficial = K × ΔP / (μ × L)
→ K = u_superficial × μ × L / ΔP
```

- **μ** = ν × ρ = 3.52e-5 × 0.746 ≈ 2.63e-5 Pa·s  
- **L** = L_measure = 0.107 m (측정 구간)

---

## 2. 방법별 K 산출

| 방법 | u_superficial | ΔP | K_sim |
|------|----------------|-----|-------|
| A (저유속 inlet) | u_in = 0.0123 m/s | ΔP_sim (수렴값) | K_sim(A) = u_in × μ × L / ΔP_sim |
| B (주기BC) | Q_phys / A_duct, Q_phys = Q_lb×dx³/dt | ΔP_target = 3.819 Pa | K_sim(B) = u_superficial × μ × L / ΔP_target |

- **A:** `run_l2_ref6x6_plan17v.py` 수렴 후 출력 `[L2-C] K_sim(A) = ... m²`  
- **B:** `run_l2_periodic_plan19v.py` 수렴 후 출력 `[L2-C] K_sim(B) = ... m²`

---

## 3. 이론 K (참고)

6×6 직선 채널 개략 추산 (plan_1.91V §2.3):

- 단일 정사각 채널 a=3.2 mm: K_single ≈ a² × 0.03515 ≈ 3.60e-7 m²  
- 유효 투과율: K_eff = K_single × ε ≈ 2.27e-7 m² (ε=0.6295)

시뮬 K와 이론 K는 형상·공극률 정의에 따라 차이 가능. **A와 B 간 K_sim 차이 < 10%**이면 교차검증 PASS.

---

## 4. PASS 기준

| 검증 | 기준 |
|------|------|
| L2-C | \|K_sim(A) − K_sim(B)\| / mean(K) < 10% |

A, B 각각 수렴 실행 후 위 식으로 비교.

# plan_1.91V §3.3–3.4: Gyroid 이론 ΔP 추산

**목적:** Gyroid(a=5, t=0.3)에 대해 이론 ΔP를 추산하여 시뮬과 정성 비교(±30~50%). Kozeny-Carman은 입상층 기반이라 TPMS에 정확하지 않을 수 있음.

---

## 1. Kozeny-Carman (plan_1.91V §3.3)

```
ΔP/L = 180 × μ × u_s × (1-ε)² / (ε³ × Dp²)
Dp = 6(1-ε) / S_v
```

- **μ** = 2.63e-5 Pa·s (200°C 공기, ν×ρ)
- **u_s** = superficial velocity = u_in (덕트 단면 기준)
- **ε** = 공극률 (커널 실측)
- **S_v** = 비표면적 [1/m] (커널 실측)

예: ε=0.5, S_v=2000 1/m → Dp = 6×0.5/2000 = 1.5e-3 m.  
ΔP/L = 180 × 2.63e-5 × u_s × 0.25 / (0.125 × 2.25e-6) = … (u_s 대입).

---

## 2. TPMS 전용 상관식 (plan_1.91V §3.4)

문헌: Femmer et al., Al-Ketan et al., Peng et al. 등에서 **K = C × a² × ε^n** 형태의 Gyroid 투과율 상관식 제시.  
에이전트가 "Gyroid permeability correlation"으로 검색하여 적용.  
정확한 C, n은 논문별로 상이하므로 여기서는 **실측 ε·S_v로 Kozeny-Carman만 적용**하고, 문헌 상관식은 추후 보정용으로 추가.

---

## 3. 사용 절차

1. `gyroid_epsilon_Sv_plan191v.py`로 **ε, S_v** 실측.
2. **Kozeny-Carman**으로 ΔP_theory 추산 (u_s = GHSV에 대응하는 u_in).
3. 주기BC 시뮬 ΔP_sim(또는 g로 부여한 ΔP)과 비교. **±50% 이내**면 정성적 일치로 간주.

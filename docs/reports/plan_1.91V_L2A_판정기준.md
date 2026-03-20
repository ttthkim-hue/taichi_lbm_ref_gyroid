# plan_1.91V Phase 1: L2-A 수렴 판정 기준

**대상:** L2 저유속 131격자 (`run_l2_ref6x6_plan17v.py`)  
**목적:** 수렴 후 4항목 판정. 2개 이상 충족 시 Phase 2 진행.

---

## 판정 기준 (plan_1.91V §1.1)

| 항목 | 조건 | PASS |
|------|------|------|
| ΔP 오차 | \|ΔP_sim − ΔP_theory\| / ΔP_theory < 5% | ✅ |
| CV (채널 유량 편차) | 36채널 대비 최대 편차 < 5% | ✅ |
| clips | outlet_clips = 0 | ✅ |
| Δρ_lbm | 수렴 시점 Δρ_lbm < 3% | ✅ |

- **ΔP_theory:** 0.153 Pa (HP Fanning, 131격자 u_in 맞춤).
- **PASS 시** → Phase 2 (방법 B 주기BC, 방법 C K 교차비교) 진행.
- **FAIL 시** → 로그에서 Δρ, Q 균형, 수렴 추이 확인 후 원인 분석.

---

## 실행·확인

```bash
python scripts/run_l2_ref6x6_plan17v.py 2>&1 | tee run_l2_plan17v_log.txt
```

수렴 후 터미널 마지막 블록의 ΔP_sim, 오차, 채널 유량 편차, clips 및 로그의 [ΔP] Δρ_lbm(%)를 위 기준과 대조.

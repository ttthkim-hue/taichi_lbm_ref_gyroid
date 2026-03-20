# plan_1.92V (plan_2.1V) 컨텍스트 압축요약

**목적:** 6시간 자리 비움 → GPU 무인 배치 실행 → 귀환 후 결과 요약으로 판정 확인.

---

## 0. 현재 상태 (계획서 §0)

| 항목 | 상태 |
|------|------|
| dt τ기반 고정 | ✅ p_scale=7.68 |
| L1 빈 덕트 | ✅ PASS (오차 7.5%) |
| L2 131 저유속 | 🔄 수렴 필요 (Δρ=0.37%) |
| 주기BC + Guo forcing | ✅ 구현됨, 미검증 |
| Gyroid ε, S_v | ✅ ε=0.806, S_v=2537 |
| Gyroid 3-GHSV | 스크립트 → **g 3개 방식**으로 전환됨 |

---

## 1. 배치 구조 (5단계)

| Step | 스크립트 | 로그 파일 | 예상 시간 |
|------|----------|-----------|-----------|
| 1 | run_l2_ref6x6_plan17v.py | 01_L2A_low_velocity.txt | ~70분 |
| 2 | run_l2_periodic_plan19v.py | 02_L2B_periodic.txt | ~70분 |
| 3 | run_l1_quick_plan19v.py | 03_L1_quick.txt | ~30분 |
| 4 | run_gyroid_3ghsv_plan191v.py | 04_gyroid_3ghsv.txt | ~210분 |
| 5 | summarize_batch_plan21v.py | 05_final_summary.txt | ~1분 |

**합계:** ~6시간 20분. 로그 디렉터리: `logs/batch_${TIMESTAMP}/`.

---

## 2. 스크립트별 요구사항 요약

- **Step 1 (L2-A):** NX=NY=131, dt τ기반, u_in 저유속(Δρ<3%), 수렴 시 `[결과] K_sim(A) = {:.4e} m²` 출력.
- **Step 2 (L2-B):** 주기BC, ΔP_target=3.819 Pa, u_superficial=Q_phys/A_duct, `[결과] K_sim(B) = {:.4e} m²` 출력.
- **Step 3 (L1):** 5000 step, ΔP ≈ 0.07 Pa 확인, dt τ기반 유지.
- **Step 4 (Gyroid):** g_lbm 3개(1e-6, 5e-6, 2e-5), 각각 u_mean·ΔP·K 산출, K 편차 < 10% → PASS/FAIL.
- **요약 스크립트:** 각 로그 마지막 30줄에서 판정/오차/PASS/FAIL/K_sim/ΔP/u_mean/CV/결과 등 키워드 추출.

---

## 3. 실행 전 체크리스트 (§6)

1. L2-A: dt 고정, K_sim(A) 및 [결과] 출력  
2. L2-B: NX=NY=131, K_sim(B) 및 [결과] 출력  
3. L1: dt 고정, 5000스텝  
4. Gyroid: g 3개, K 산출, 편차 판정  
5. summarize_batch_plan21v.py 생성  
6. run_batch_plan21v.sh 생성 및 chmod +x  
7. 에러 시 traceback 출력 (try-except 시 재발생 권장)  
8. GPU 메모리 ~2.4GB 수준 확인  
9. nohup 실행 후 batch_log.txt 초기 출력 확인  

---

## 4. 귀환 후 확인

```bash
cat logs/batch_*/05_final_summary.txt
```

PASS 기준: L2-A ΔP·CV·Δρ, L2-B u_mean 오차 <5%, L2-C K(A) vs K(B) <10%, L1 ΔP 0.05~0.09 Pa, Gyroid K 편차 <10%.

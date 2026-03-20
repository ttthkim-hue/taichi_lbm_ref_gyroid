# plan_1.91V (plan_2.0V) 완수 요약

**기준 문서:** `docs/plan_1.91V.md`  
**완수일:** 2026-03-18

---

## 1. 수행 항목

| Phase | 항목 | 내용 | 상태 |
|-------|------|------|------|
| 1 | L2-A 판정 기준 | ΔP<5%, CV<5%, clips=0, Δρ<3% 문서화 | ✅ |
| 2 | L2-B 주기BC | u_target=0.449 m/s, K_sim(B) 출력 | ✅ |
| 2 | L2-C K 교차비교 | K=u·μ·L/ΔP, A·B 비교 문서 | ✅ |
| 2 | 출구 vz 저장 | plan17v에 vz_outlet_l2_131.npy 저장 | ✅ |
| 3 | Gyroid ε·S_v | gyroid_epsilon_Sv_plan191v.py | ✅ |
| 3 | Gyroid 이론 ΔP | Kozeny-Carman·문헌 문서 | ✅ |
| 3 | Gyroid 3-GHSV | run_gyroid_3ghsv_plan191v.py | ✅ |

---

## 2. 생성·수정 파일

| 파일 | 내용 |
|------|------|
| `docs/plan_1.91V_L2A_판정기준.md` | Phase1 4항목 판정 기준 |
| `docs/plan_1.91V_L2_K_교차비교.md` | K 산출식, A·B 비교 기준 |
| `docs/plan_1.91V_Gyroid_이론_ΔP.md` | Kozeny-Carman, TPMS 문헌 메모 |
| `scripts/run_l2_periodic_plan19v.py` | u_channel 0.449, K_sim(B) 출력 |
| `scripts/run_l2_ref6x6_plan17v.py` | CV<5%, Δρ<3%, K_sim(A), vz_out 저장 |
| `scripts/gyroid_epsilon_Sv_plan191v.py` | a=5,t=0.3 ε·S_v 실측 |
| `scripts/run_gyroid_3ghsv_plan191v.py` | 3-GHSV 주기BC, K 일정성 판정 |
| `.cursor-tasks.md` | plan_1.91V 체크리스트 |

---

## 3. 실행 순서 (사용자)

```
# Phase 1
python scripts/run_l2_ref6x6_plan17v.py 2>&1 | tee run_l2_plan17v_log.txt   # 수렴 후 L2-A 판정

# Phase 2
python scripts/run_l2_periodic_plan19v.py 2>&1 | tee run_l2_periodic_log.txt
# 로그에서 K_sim(A), K_sim(B) 비교 → L2-C < 10%

# Phase 3
python scripts/gyroid_epsilon_Sv_plan191v.py   # ε, S_v 기록
python scripts/run_gyroid_3ghsv_plan191v.py    # 3-GHSV, K 일정성
```

---

## 4. PASS 기준 종합 (plan_1.91V §5)

| 검증 | 방법 | PASS 기준 |
|------|------|-----------|
| L2-A | Velocity inlet 저유속 | ΔP<5%, CV<5%, Δρ<3%, clips=0 |
| L2-B | 주기BC | u_mean vs 0.449 m/s < 5% |
| L2-C | K 교차비교 | K_sim(A) vs K_sim(B) < 10% |
| Gyroid-1 | 이론 비교 | Kozeny-Carman 대비 ±50% (정성) |
| Gyroid-2 | 3-GHSV | 3개 K 차이 < 10% |

**L2 A+B+C 중 2개 이상 PASS → 솔버 검증 완료.**

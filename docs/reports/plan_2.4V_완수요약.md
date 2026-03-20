# plan_2.4V 완수 요약

**기준:** docs/plan_2.4V.md (Gyroid 검증 + GCI → BO 진입)

---

## 완료한 작업

### 1. run_gyroid_3ghsv_plan191v.py 수정 (§4.1)

| 수정 | 적용 내용 |
|------|-----------|
| max_steps | 80,000 → **20,000** |
| log_interval | 2,000 → **1,000** |
| Guo 수정 여부 | docstring·실행 시 1행 출력으로 **Guo 수정 솔버 사용** 명시 |
| K 산출 | u_superficial = Q_phys/A_DUCT, K = u_superficial×μ×L/dP (L = NZ×dx) |
| 편차·판정 | 3개 K 편차(%) 출력, PASS/FAIL (기준 < 10%) |

### 2. run_gci_3level_plan14v.py 수정 (§4.2)

| 수정 | 적용 내용 |
|------|-----------|
| LEVELS | **Coarse** dx=0.4 mm, 66×66×275 / **Medium** 0.2 mm, 131×131×550 / **Fine** 0.15 mm, 175×175×733 |
| max_steps | **20,000** |
| 모드 | **periodic_body_force** |
| g_lbm | **5e-6** (3-g mid와 동일) |
| 형상 | Gyroid a=5 mm, t=0.3, 각 레벨에서 set_geometry_gyroid_kernel로 해당 dx 재생성 |
| 산출 | 레벨별 **K** 기록 → Richardson p, **GCI_fine(%)** 산출, PASS/FAIL (GCI < 5%) |

---

## 실행 순서 (plan §3)

```bash
# Step 1: Gyroid 3-g (~60분) — 실행 시작됨
python scripts/run_gyroid_3ghsv_plan191v.py 2>&1 | tee logs/gyroid_3g.txt

# Step 2: Gyroid 완료 후 GCI 3-level (~80분)
python scripts/run_gci_3level_plan14v.py 2>&1 | tee logs/gci_3level.txt
```

- **Gyroid 3-g:** 백그라운드로 실행 시작. 완료 시 `logs/gyroid_3g.txt`에 K 3개·편차·판정 기록.
- **GCI:** Gyroid가 끝난 뒤 순차 실행. `logs/gci_3level.txt`에 3격자 K, p, GCI(%), 판정 기록.

---

## 체크리스트 (plan §체크리스트)

| 순서 | 항목 | PASS 기준 | 상태 |
|------|------|-----------|------|
| 1 | Gyroid 3-g 완료 확인 | K 편차 < 10% | 🔄 실행 중 |
| 2 | GCI 3-level 실행 | GCI < 5% | ⏳ Gyroid 완료 후 |
| 3 | BO 파이프라인 구축 | — | ☐ 전부 PASS 후 |

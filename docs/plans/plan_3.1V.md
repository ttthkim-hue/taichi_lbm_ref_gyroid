# 작업지시서 — plan_3.2V (야간 10시간 종합 실행)

**작성일:** 2026-03-19  
**실행 시간:** 22:00 ~ 익일 08:00 (약 10시간)  
**목표:** BO 재실행 + 다중 GHSV + 유동 특성화 + 데이터 신뢰성 확보

---

## 0. 시간 예산

케이스당 ~2분 (a 작음) ~ ~4분 (a=12) → **평균 3분**  
10시간 = 600분 → **최대 ~200 케이스** 실행 가능

| Phase | 내용 | 케이스 수 | 예상 시간 |
|-------|------|-----------|-----------|
| 1 | BO 재실행 (100회) | 100 | ~4시간 |
| 2 | 다중 GHSV (Top-5 × 5조건) | 25 | ~1시간 |
| 3 | Forchheimer 고유속 (Top-5 × 5g) | 25 | ~1시간 |
| 4 | 유동 특성화 + VTI (Top-5) | 5 | ~0.5시간 |
| 5 | 반복 재현성 검증 (5점 × 3회) | 15 | ~0.5시간 |
| 6 | 설계 공간 경계 보강 (20점) | 20 | ~1시간 |
| 버퍼 | 오류/재실행 여유 | — | ~2시간 |
| **합계** | | **~190** | **~10시간** |

---

## 1. Phase 1: BO 재실행 (100회, ~4시간)

### 1.1 수정 사항 (plan_3.1V 반영)

```python
# run_bo_pipeline.py 수정:
dimensions = [Real(3.0, 12.0, name='a'),    # 상한 8→12 확장
              Real(-0.5, 0.5, name='t')]

# Acquisition 강화:
result = gp_minimize(
    objective,
    dimensions,
    n_calls=100,         # 총 100회
    n_initial_points=20, # 초기 탐색 20회
    acq_func="LCB",
    acq_func_kwargs={"kappa": 3.0},  # 기본 1.96→3.0 (exploration↑)
    random_state=42
)
```

### 1.2 실행

```bash
PYTHONUNBUFFERED=1 python scripts/run_bo_pipeline.py \
    --n_init 20 --n_iter 80 \
    --a_min 3.0 --a_max 12.0 \
    --output results/bo_results_v2.csv \
    2>&1 | tee logs/bo_v2.txt
```

### 1.3 완료 후 자동 실행 (Pareto + Top-5)

```bash
python scripts/analyze_pareto.py --input results/bo_results_v2.csv --top 5
```

Top-5를 뽑는 이유: Phase 2~4에서 다중 조건 분석용.

| 설계 | 기준 |
|------|------|
| A | S_v 최대 |
| B | ΔP 최소 |
| C | TOPSIS 유토피아 거리 최소 (균형) |
| D | ε ≈ 0.50 중 S_v 최대 (중간 공극률) |
| E | a ≈ 5~6mm 중 최적 (제조 현실성 고려) |

---

## 2. Phase 2: 다중 GHSV 압력손실 특성 (~1시간)

### 2.1 목적

동일 Gyroid 구조에서 GHSV 변화에 따른 ΔP 특성. 논문 Table/Figure로 직접 사용.

### 2.2 GHSV 조건

| GHSV [h⁻¹] | u_in [m/s] | 적용 분야 |
|-------------|------------|-----------|
| 5,000 | 0.139 | 저속 운전 (저부하) |
| 10,000 | 0.278 | **기준 조건** |
| 20,000 | 0.556 | 고부하 |
| 40,000 | 1.111 | 고속 디젤 |
| 60,000 | 1.667 | 극한 조건 |

### 2.3 방법

**Darcy 영역이면 시뮬 불필요.** K는 유속 무관 → ΔP = u·μ·L/K로 직접 환산.

```python
# Top-5 각각에 대해:
for ghsv in [5000, 10000, 20000, 40000, 60000]:
    u_in = ghsv / 3600  # [m/s] (L=1m 기준, 실제는 GHSV·L_cat)
    dP = u_in * mu * L_cat / K
```

**단, 고유속에서 Darcy 이탈 여부를 Phase 3에서 확인해야 함.**

### 2.4 출력

`results/ghsv_sensitivity.csv`:

```
design, a, t, K, GHSV, u_in, dP_darcy, Re_pore
```

---

## 3. Phase 3: Forchheimer 비선형 영역 탐색 (~1시간)

### 3.1 목적

고유속에서 Darcy 법칙이 깨지는지 확인. 깨지면 Forchheimer 계수(β)를 추출하여 논문 가치를 높임.

### 3.2 이론

```
Darcy:       ΔP/L = μ·u / K
Forchheimer: ΔP/L = μ·u / K + β·ρ·u²

→ (ΔP/L) / u = μ/K + β·ρ·u
→ y = a + b·x  (선형 회귀로 K, β 동시 추출)
```

### 3.3 설정

Top-5 각 설계에 대해 **5가지 g_lbm**으로 시뮬:

| g_lbm | 예상 Re_pore | 영역 |
|-------|-------------|------|
| 1e-6 | ~0.006 | 순수 Darcy |
| 5e-6 | ~0.03 | Darcy (검증 완료) |
| 5e-5 | ~0.3 | Darcy 경계 |
| 5e-4 | ~3 | 천이 |
| 2e-3 | ~12 | 관성 (Forchheimer) |

> ⚠️ g=5e-4, 2e-3에서 Ma 확인 필요. Ma > 0.1이면 LBM 압축성 오차 증가.
> Ma = u_lbm / cs ≈ u_lbm / 0.577. u_lbm < 0.05면 안전.

### 3.4 스크립트

`scripts/run_forchheimer.py` 신규 작성:

```python
"""
Top-5 설계에 대해 5가지 g로 시뮬 → K, β 추출.
25 케이스 (5설계 × 5g), 케이스당 ~2분.
"""
# 각 (설계, g) 조합:
#   1. 솔버 리셋
#   2. 주기BC + body force
#   3. 수렴 후 u_sup, dP 산출
#   4. (dP/L)/u vs u 선형회귀 → K, β

# 출력:
# results/forchheimer.csv:
#   design, a, t, g_lbm, u_sup, dP_L, Re_pore, Ma_lbm
# results/forchheimer_fit.csv:
#   design, a, t, K_darcy, beta, R2, Re_transition
```

### 3.5 논문 가치

**Forchheimer β를 보고하면 논문의 실용적 기여도가 크게 올라감.**
"저유속(GHSV 5k~20k)에서는 Darcy, 고유속(GHSV 40k+)에서는 Forchheimer 보정이 필요하다"는 결론은 SCR 설계 엔지니어에게 직접적으로 유용.

---

## 4. Phase 4: 유동 특성화 + VTI (~30분)

### 4.1 목적

Top-5 설계의 유동 패턴 분석. **2차 유동(secondary flow), 혼합 지표** 산출.

### 4.2 산출 지표

| 지표 | 정의 | 물리적 의미 |
|------|------|-------------|
| v_trans/v_z | √(vx² + vy²) / \|vz\| | 횡방향 유동 비율 (혼합 강도) |
| ω_z | ∂vy/∂x - ∂vx/∂y | Z방향 와도 (Dean-like 와류) |
| σ_vz | std(vz) / mean(vz) | 유속 불균일도 |
| tortuosity τ | L_path / L_straight | 유로 꼬임도 (>1이면 경로 길어짐) |

### 4.3 코드 구조

```python
# 수렴 후 유동장에서:
vel = core.vel.to_numpy()  # (NX, NY, NZ, 3)
solid = core.solid.to_numpy()
fluid_mask = (solid == 0)

vx = vel[:,:,:,0][fluid_mask]
vy = vel[:,:,:,1][fluid_mask]
vz = vel[:,:,:,2][fluid_mask]

# 횡방향 유동 비율
v_trans = np.sqrt(vx**2 + vy**2)
mixing_ratio = np.mean(v_trans) / np.mean(np.abs(vz))

# 유속 불균일도
vz_nonzero = vz[np.abs(vz) > 1e-10]
uniformity = np.std(vz_nonzero) / np.mean(vz_nonzero)
```

### 4.4 Dean 와류 / 카오틱 믹싱 가능성

**현재 Re_pore ≈ 0.03에서는 Dean 와류가 나타나지 않습니다.** Dean 수 De = Re·√(d/R)이고, De > 40~60에서 2차 유동이 발생. 현재 Re가 너무 낮음.

하지만 **Phase 3에서 g를 키워 Re_pore ≈ 3~12로 올리면:**

| Re_pore | 예상 현상 |
|---------|-----------|
| < 1 | 순수 Stokes/Darcy, 혼합 없음 |
| 1~10 | 약한 관성 효과, Gyroid 곡률에 의한 경로 편향 |
| 10~100 | **정상 2차 유동** (Dean-like), Forchheimer 영역 |
| > 100 | 비정상 와류, 난류 전이 (현재 LBM으로도 해석 가능) |

**Phase 3의 고Re 케이스에서 v_trans/v_z를 함께 측정하면**, "Re 증가에 따른 혼합 강도 변화"를 보고할 수 있음. 이건 단순 ΔP 최적화를 넘어서는 **유동 물리 분석**으로 논문 가치를 높임.

### 4.5 출력

```
results/flow_metrics.csv:
  design, a, t, Re_pore, mixing_ratio, uniformity, tortuosity

results/top5_A_vz_xy.png    ← vz 단면
results/top5_A_vtrans_xy.png ← 횡방향 유동 단면
results/top5_A_omega_xy.png  ← 와도 단면
... (B, C, D, E 각각)
```

---

## 5. Phase 5: 반복 재현성 검증 (~30분)

### 5.1 목적

동일 (a, t)에서 **솔버 리셋 후 3회 반복** → K 재현성 확인. 논문에서 "수치 불확실성"으로 보고.

### 5.2 설정

Pareto front에서 5개 대표점 선택 × 3회 반복 = 15 케이스

```python
repeat_points = [
    (3.5, 0.1),   # 소 단위셀
    (5.0, 0.0),   # 중간
    (5.0, 0.3),   # 기준 (3-g 검증과 동일)
    (8.0, -0.3),  # 대 단위셀
    (10.0, -0.2), # 확장 영역 (신규)
]
```

### 5.3 PASS 기준

```
각 점에서 3회 K의 CV(변동계수) < 0.1%
CV = std(K) / mean(K) × 100
```

### 5.4 출력

```
results/repeatability.csv:
  a, t, run, K, dP, S_v

results/repeatability_summary.csv:
  a, t, K_mean, K_std, CV_pct
```

---

## 6. Phase 6: 설계 공간 경계 보강 (~1시간)

### 6.1 목적

BO가 탐색하지 않은 영역을 격자식으로 채워, **응답면(Response Surface) 신뢰도 향상**.

### 6.2 설정

```python
# BO가 놓친 영역 보강 (특히 a=9~12 구간)
a_grid = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
t_grid = [-0.3, 0.0, 0.3]
# 중복 제외 후 ~20점
```

### 6.3 출력

```
results/grid_supplement.csv
```

BO 결과와 합쳐서 최종 응답면 구성:

```python
df_all = pd.concat([bo_results, grid_supplement])
# → GP 응답면 재학습 → S_v(a,t), K(a,t) contour plot
```

---

## 7. 전체 실행 스크립트 (단일 파이프라인)

```bash
#!/bin/bash
# run_overnight.sh — 야간 10시간 자동 실행
set -e
cd /mnt/h/taichi_lbm_ref_gyroid
source .venv_v32/bin/activate
export PYTHONUNBUFFERED=1

echo "=== Phase 1: BO 재실행 (100회) ==="
python scripts/run_bo_pipeline.py \
    --n_init 20 --n_iter 80 \
    --a_min 3.0 --a_max 12.0 \
    --output results/bo_results_v2.csv \
    2>&1 | tee logs/phase1_bo.txt

echo "=== Phase 1b: Pareto 분석 ==="
python scripts/analyze_pareto.py \
    --input results/bo_results_v2.csv \
    --top 5 \
    2>&1 | tee logs/phase1b_pareto.txt

echo "=== Phase 2: 다중 GHSV ==="
python scripts/run_ghsv_sensitivity.py \
    --pareto results/pareto_front.csv \
    --output results/ghsv_sensitivity.csv \
    2>&1 | tee logs/phase2_ghsv.txt

echo "=== Phase 3: Forchheimer ==="
python scripts/run_forchheimer.py \
    --pareto results/pareto_front.csv \
    --output results/forchheimer.csv \
    2>&1 | tee logs/phase3_forch.txt

echo "=== Phase 4: 유동 특성화 ==="
python scripts/run_flow_metrics.py \
    --pareto results/pareto_front.csv \
    --output results/flow_metrics.csv \
    2>&1 | tee logs/phase4_flow.txt

echo "=== Phase 5: 반복 재현성 ==="
python scripts/run_repeatability.py \
    --output results/repeatability.csv \
    2>&1 | tee logs/phase5_repeat.txt

echo "=== Phase 6: 경계 보강 ==="
python scripts/run_grid_supplement.py \
    --output results/grid_supplement.csv \
    2>&1 | tee logs/phase6_grid.txt

echo "=== 전체 완료 ==="
echo "결과 파일:"
ls -lh results/*.csv results/*.png
```

### 7.1 실행

```bash
nohup bash run_overnight.sh > logs/overnight.txt 2>&1 &
echo "PID: $!"
```

### 7.2 익일 아침 확인

```bash
# 완료 여부
tail -20 logs/overnight.txt

# 각 Phase 결과 요약
wc -l results/bo_results_v2.csv      # 101 (헤더+100)
wc -l results/forchheimer.csv         # 26 (헤더+25)
wc -l results/repeatability.csv       # 16 (헤더+15)
cat results/pareto_front.csv | head
cat results/forchheimer_fit.csv
```

---

## 8. 신규 스크립트 목록

| 스크립트 | Phase | 역할 | 입력 | 출력 |
|----------|-------|------|------|------|
| `run_bo_pipeline.py` (수정) | 1 | a∈[3,12], LCB kappa=3.0 | — | bo_results_v2.csv |
| `analyze_pareto.py` (수정) | 1b | TOPSIS Top-C, Top-5 | bo_results_v2.csv | pareto_front.csv, PNG |
| `run_ghsv_sensitivity.py` (신규) | 2 | Darcy 환산 5조건 | pareto_front.csv | ghsv_sensitivity.csv |
| `run_forchheimer.py` (신규) | 3 | 5g × 5설계, K·β 추출 | pareto_front.csv | forchheimer.csv, forchheimer_fit.csv |
| `run_flow_metrics.py` (신규) | 4 | 혼합지표, 와도, VTI | pareto_front.csv | flow_metrics.csv, PNG |
| `run_repeatability.py` (신규) | 5 | 5점 × 3회 반복 | — | repeatability.csv |
| `run_grid_supplement.py` (신규) | 6 | 10×3 격자 보강 | — | grid_supplement.csv |
| `run_overnight.sh` (신규) | 전체 | Phase 1~6 순차 실행 | — | logs/*.txt |

---

## 9. 논문에 반영되는 데이터

| Phase | 논문 활용 | 예상 Table/Figure |
|-------|-----------|-------------------|
| 1 | Pareto front (핵심 결과) | Fig.3 S_v vs ΔP |
| 2 | GHSV별 ΔP 표 | Table 3 |
| 3 | Forchheimer β, Re 전이 | Fig.6 (ΔP/L)/u vs u |
| 4 | 혼합 지표 비교 | Table 4, Fig.7 |
| 5 | 수치 불확실성 | §4.6 한 문단 |
| 6 | 응답면 contour | Fig.4 S_v(a,t), Fig.5 K(a,t) |

---

## 10. 익일 아침 체크리스트

| 순서 | 확인 항목 | 파일 | 기준 |
|------|-----------|------|------|
| 1 | BO 100회 완료 | bo_results_v2.csv 행 ≥ 100 | ☐ |
| 2 | 경계 갇힘 해소 | a 분포가 3~12 골고루 | ☐ |
| 3 | Pareto 점 ≥ 15개 | pareto_front.csv | ☐ |
| 4 | Top-C ≠ Top-B | TOPSIS 결과 | ☐ |
| 5 | Forchheimer β 추출 | forchheimer_fit.csv, R² > 0.99 | ☐ |
| 6 | 재현성 CV < 0.1% | repeatability_summary.csv | ☐ |
| 7 | 고Re Ma < 0.1 | forchheimer.csv Ma 컬럼 | ☐ |
| 8 | VTI/PNG 생성 | results/top5_*.png 존재 | ☐ |
| 9 | 6×6 Reference 비교점 | pareto_plot에 표시 | ☐ |
| 10 | 전체 에러 없음 | logs/overnight.txt 끝에 "전체 완료" | ☐ |
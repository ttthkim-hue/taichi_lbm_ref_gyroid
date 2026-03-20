# 작업지시서 — plan_3.0V (BO 본 실행 + Pareto 분석)

**작성일:** 2026-03-19  
**전제:** 검증 3/3 PASS (NZ 무관성 0.00%, 3-g 편차 0.06%, GCI 3.60%)

---

## 0. 검증 완료 현황

| 검증 | 결과 | 의미 |
|------|------|------|
| NZ 무관성 | K 차이 **0.00%** | 단축 도메인 물리적으로 동치 |
| 3-g 스케일링 | K 편차 **0.06%** | Darcy 법칙 완벽 성립 |
| GCI | **3.60%** | Medium 격자 충분 |
| BO 스모크 | 2회 성공 | 파이프라인 정상 작동 |

**솔버 무결성 확인 완료. BO 실행 가능.**

---

## 1. BO 본 실행

### 1.1 실행 명령

```bash
cd /mnt/h/taichi_lbm_ref_gyroid
source .venv_v32/bin/activate
PYTHONUNBUFFERED=1 python scripts/run_bo_pipeline.py \
    --n_init 15 --n_iter 35 \
    --output results/bo_results.csv \
    2>&1 | tee logs/bo_full.txt
```

### 1.2 설정 확인

| 항목 | 값 |
|------|-----|
| 초기 탐색 | 15회 (랜덤/LHS) |
| BO 반복 | 35회 |
| **총 평가** | **50회** |
| 설계 변수 | a ∈ [3, 8] mm, t ∈ [−0.5, 0.5] |
| 제약 | ε ∈ [0.35, 0.65] (위반 시 penalty) |
| 목적함수 | −w₁·(S_v/ref) + w₂·(K⁻¹/ref) |
| 도메인 | NX=NY=131, NZ=round(2a/dx) |
| 케이스당 시간 | ~2분 |
| **총 예상** | **~100분 (~1.5시간)** |

### 1.3 출력 CSV 컬럼

```
idx, a, t, NZ, epsilon, S_v, K, u_sup, dP_darcy, feasible, elapsed_s
```

`dP_darcy`는 GHSV 10,000(u_in=0.2778) 기준 환산값:

```
dP_darcy = 0.2778 × 2.626e-5 × 0.1 / K
```

### 1.4 중간 모니터링

```bash
# 진행 상황 확인 (다른 터미널)
tail -f logs/bo_full.txt

# CSV 행 수 확인
wc -l results/bo_results.csv
```

---

## 2. BO 완료 후 Pareto 분석

### 2.1 분석 스크립트

`scripts/analyze_pareto.py` 신규 작성:

```python
"""
BO 결과 CSV에서 Pareto front 추출 + 시각화.
입력: results/bo_results.csv
출력: 
  - results/pareto_front.csv (Pareto 최적 점)
  - results/pareto_plot.png (S_v vs ΔP 산점도)
  - results/pareto_params.png (a, t 분포)
"""
```

### 2.2 Pareto front 추출

```python
# 2-목적: S_v 최대화, dP 최소화
# → Pareto: S_v↑이면서 dP↓인 비지배 해

import pandas as pd
import numpy as np

df = pd.read_csv("results/bo_results.csv")
feasible = df[df['feasible'] == 'OK']

# Pareto 판별
def is_pareto(costs):
    """costs: (n, 2), 최소화 기준. 비지배 해 인덱스 반환."""
    is_efficient = np.ones(len(costs), dtype=bool)
    for i, c in enumerate(costs):
        if is_efficient[i]:
            is_efficient[is_efficient] = np.any(costs[is_efficient] < c, axis=1)
            is_efficient[i] = True
    return is_efficient

# S_v 최대화 → -S_v 최소화, dP 최소화 → dP 최소화
costs = np.column_stack([-feasible['S_v'].values, feasible['dP_darcy'].values])
pareto_mask = is_pareto(costs)
pareto = feasible[pareto_mask].sort_values('S_v')
pareto.to_csv("results/pareto_front.csv", index=False)
```

### 2.3 시각화 (pyvista/matplotlib)

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 1. S_v vs ΔP (Pareto front)
ax = axes[0]
ax.scatter(feasible['dP_darcy'], feasible['S_v'], c='gray', alpha=0.5, label='Feasible')
ax.scatter(pareto['dP_darcy'], pareto['S_v'], c='red', s=80, label='Pareto')
ax.set_xlabel('ΔP [Pa] (GHSV 10k)')
ax.set_ylabel('S_v [1/m]')
ax.set_title('Pareto Front: S_v vs ΔP')
ax.legend()

# 2. a vs t (설계 공간)
ax = axes[1]
sc = ax.scatter(feasible['a'], feasible['t'], c=feasible['S_v'], cmap='viridis', alpha=0.6)
ax.scatter(pareto['a'], pareto['t'], c='red', s=80, edgecolors='black', zorder=5)
ax.set_xlabel('a [mm]')
ax.set_ylabel('t')
ax.set_title('설계 공간 (색상: S_v)')
plt.colorbar(sc, ax=ax)

# 3. ε vs K
ax = axes[2]
ax.scatter(feasible['epsilon'], feasible['K'], c='gray', alpha=0.5)
ax.scatter(pareto['epsilon'], pareto['K'], c='red', s=80)
ax.set_xlabel('ε (공극률)')
ax.set_ylabel('K [m²]')
ax.set_title('공극률 vs 투과율')
ax.set_yscale('log')

plt.tight_layout()
plt.savefig('results/pareto_plot.png', dpi=150)
print("저장: results/pareto_plot.png")
```

> ⚠️ 위 코드는 의도 전달용. 실제 CSV 컬럼명에 맞춰 수정.

---

## 3. Pareto 최적 설계 Top-3 상세 분석

### 3.1 Top-3 선정 기준

Pareto front에서 아래 3가지 대표 설계 선정:

| 설계 | 선정 기준 | 특성 |
|------|-----------|------|
| A | S_v 최대 | 촉매 반응 극대화 (ΔP 높음) |
| B | ΔP 최소 | 송풍기 동력 최소화 (S_v 낮음) |
| C | S_v/ΔP 최대 (무차원 효율) | 균형 설계 |

### 3.2 Top-3 VTI 시각화

각 설계에 대해 5000스텝 실행 후 VTR 저장:

```python
# Top-3 설계 (a, t) 추출 후:
for design in top3:
    # 솔버 생성, Gyroid 커널, 주기BC
    # 수렴까지 실행
    # VTR 저장: results/top3_A.vtr, top3_B.vtr, top3_C.vtr
    # pyvista 시각화: vz 단면, solid 단면
```

---

## 4. 논문 결과 섹션 데이터 체크리스트

| 데이터 | 출처 | 상태 |
|--------|------|------|
| 검증 결과 표 (L1, L2-B, NZ, 3-g, GCI) | plan_2.6V | ✅ |
| BO 결과 CSV (50 points) | run_bo_pipeline.py | ☐ 실행 후 |
| Pareto front CSV | analyze_pareto.py | ☐ 분석 후 |
| Pareto plot (S_v vs ΔP) | analyze_pareto.py | ☐ |
| Top-3 파라미터 표 | pareto_front.csv | ☐ |
| Top-3 유동장 VTR/PNG | Top-3 스크립트 | ☐ |
| 설계 공간 탐색 분포 | analyze_pareto.py | ☐ |

---

## 5. 실행 순서

```
1. BO 본 실행 (~100분, 백그라운드)
   → nohup으로 실행하고 다른 작업 가능

2. 완료 후 Pareto 분석 (~5분)
   → python scripts/analyze_pareto.py

3. Top-3 VTI 시각화 (~10분)
   → 3개 설계 × ~3분

4. 논문 그래프 정리
```

**총 소요: ~2시간**

---

## 6. 백그라운드 실행 (자리 비울 경우)

```bash
nohup bash -c '
source .venv_v32/bin/activate
PYTHONUNBUFFERED=1 python scripts/run_bo_pipeline.py \
    --n_init 15 --n_iter 35 \
    --output results/bo_results.csv
python scripts/analyze_pareto.py
' > logs/bo_and_pareto.txt 2>&1 &

echo "PID: $!"
```

귀환 후:

```bash
cat logs/bo_and_pareto.txt | tail -20
cat results/pareto_front.csv
```

---

## 체크리스트

| 순서 | 항목 | 예상 시간 | 결과 | 상태 |
|------|------|-----------|------|------|
| 1 | BO 본 실행 (50회) | ~100분 | 50회 완료 (47 OK / 3 FAIL), 87.7분 | ☑ PASS |
| 2 | Pareto front 추출 | ~1분 | 47 Feasible → 21 Pareto 비지배 해 | ☑ 완료 |
| 3 | Pareto 시각화 | ~5분 | pareto_plot.png, pareto_params.png | ☑ 완료 |
| 4 | Top-3 선정 + VTI | ~10분 | A(Sv=3554), B(dP=2.95), C=B | ☑ 완료 |
| 5 | 논문 데이터 정리 | — | 보고서 작성 완료 | ☑ 완료 |
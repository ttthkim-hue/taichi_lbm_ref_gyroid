# Plan 3.1V 시뮬레이션 캠페인 — 최종 종합분석보고서

| 항목 | 내용 |
|------|------|
| **저자** | Taichi-LBM Gyroid 연구팀 |
| **문서 버전** | FINAL v1.0 |
| **데이터 동결 날짜** | 2026-03-20 |
| **캠페인 코드** | plan31v (campaign_plan31v) |
| **비고** | 본 문서는 기존 `docs/reports/plan_3.1V_실행결과_상세종합분석보고서.md`를 흡수·확장한 최종본이다. |

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [물리·기하 설정](#2-물리기하-설정)
3. [코드·스크립트 경로 표](#3-코드스크립트-경로-표)
4. [Phase 1: BO 결과](#4-phase-1-bo-결과)
5. [Phase 1b: Pareto + Top-5](#5-phase-1b-pareto--top-5)
6. [Phase 2: GHSV 감도](#6-phase-2-ghsv-감도)
7. [Phase 3: Forchheimer](#7-phase-3-forchheimer)
8. [Phase 4: 유동 특성화](#8-phase-4-유동-특성화)
9. [Phase 5: 재현성](#9-phase-5-재현성)
10. [Phase 6: 격자 보강](#10-phase-6-격자-보강)
11. [계획서 §10 체크리스트 대조표](#11-계획서-10-체크리스트-대조표)
12. [논문 매핑](#12-논문-매핑)
13. [한계 및 후속 과제](#13-한계-및-후속-과제)
14. [부록: 전체 파일 경로 인벤토리](#14-부록-전체-파일-경로-인벤토리)

---

## 1. Executive Summary

Plan 3.1V 캠페인은 Gyroid 구조의 단위셀 크기 *a*와 등가면 파라미터 *t*를 설계 변수로, Bayesian Optimization(BO)을 통해 100회 LBM 시뮬레이션을 수행하고, Pareto 분석, GHSV 감도, Forchheimer 비선형 회귀, 유동 특성화, 재현성 검증, 격자 보강까지 **6개 Phase**를 야간 자동 파이프라인으로 완수한 캠페인이다.

| 항목 | 결과 |
|------|------|
| BO 평가 | 100회 완료 (`bo_results_v2.csv`) |
| Feasible OK | 85점 |
| Feasible FAIL | 15점 (주로 \|t\|~0.5 근방 및 극단 공극률) |
| Pareto 전면 | 50점 (`pareto_front.csv`) -- ">=15점" 기준 대폭 초과 |
| Top-5 선정 | A~E 완료 (`top5_selected.csv`) |
| GHSV 감도 | 5설계 x 5조건 = 25행 (`ghsv_sensitivity.csv`) |
| Forchheimer | 원시 25행; 설계 B는 고 g\_lbm에서 수치 발산, R^2~0.37 비신뢰 |
| 유동 특성화 | 5설계 지표 + top5\_\* PNG 다수 (`flow_metrics.csv`) |
| 재현성 | 5점 x 3회, CV << 0.1% -- **PASS** |
| 격자 보강 | 22점 시뮬 (`grid_supplement.csv`) |
| 파이프라인 | 2026-03-19 22:13 -> 03-20 02:34 KST (약 4.2시간), "전체 완료" 확인 |

---

## 2. 물리·기하 설정

### 2.1 솔버 설정

| 파라미터 | 값 |
|----------|-----|
| 격자 볼츠만 모형 | D3Q19 MRT-LBM |
| 프레임워크 | Taichi 1.7.4, `arch=cuda` |
| 도메인 크기 | NX = NY = 131, NZ = 2a/dx |
| 격자 간격 dx | 0.2 mm |
| 경계 조건 | 주기 BC + body force 모드 |
| Python 버전 | 3.13.2 |
| 가상환경 | `.venv_v32` |

### 2.2 Gyroid 기하 정의

Gyroid 등가면은 다음 수식으로 정의된다:

```
phi(x) = sin(2*pi*x/a)*cos(2*pi*y/a) + sin(2*pi*y/a)*cos(2*pi*z/a) + sin(2*pi*z/a)*cos(2*pi*x/a)
```

- 고체/유체 판별: `phi(x) > t` (또는 `< t`)에 따라 결정
- 등가면 파라미터 *t*: 공극률(porosity)을 제어

### 2.3 BO 설계 공간

| 변수 | 범위 |
|------|------|
| 단위셀 크기 *a* | [3.0, 12.0] mm |
| 등가면 파라미터 *t* | (-0.5, 0.5) |
| 획득함수 | LCB (Lower Confidence Bound), kappa = 3 |
| 초기 표본 | n\_init = 20 |
| 반복 수 | n\_iter = 80 |
| 최적화 엔진 | `gp_minimize` (scikit-optimize) |

---

## 3. 코드·스크립트 경로 표

| 역할 | 파일 경로 |
|------|----------|
| LBM 솔버 핵심 | `solver/taichi_lbm_core.py` |
| 솔버 패키지 init | `solver/__init__.py` |
| BO 파이프라인 | `scripts/run_bo_pipeline.py` |
| Pareto 분석 | `scripts/analyze_pareto.py` |
| GHSV 감도 | `scripts/run_ghsv_sensitivity.py` |
| Forchheimer 회귀 | `scripts/run_forchheimer.py` |
| 유동 특성화 | `scripts/run_flow_metrics.py` |
| 재현성 테스트 | `scripts/run_repeatability.py` |
| 격자 보강 | `scripts/run_grid_supplement.py` |
| 야간 오케스트레이션 | `run_overnight.sh` |
| Gyroid 마스크 생성 | `scripts/init_gyroid_mask_v32.py` |
| VTI 진단 저장 | `scripts/save_vti_gyroid_diag.py` |
| L2A VTI 저장 | `scripts/save_vti_l2a_diag.py` |

---

## 4. Phase 1: BO 결과

### 4.1 개요

Bayesian Optimization을 통해 총 **100회**의 LBM 시뮬레이션을 수행하였다.

- **설정**: a in [3.0, 12.0] mm, t in (-0.5, 0.5), LCB kappa=3, n\_init=20, n\_iter=80
- **결과 파일**: `bo_results_v2.csv`

### 4.2 집계

| 구분 | 수량 |
|------|------|
| 총 평가 횟수 | 100 |
| Feasible OK | 85 |
| Feasible FAIL | 15 |

### 4.3 설계 변수 분포

| 통계량 | a [mm] |
|--------|--------|
| 최솟값 | 3.0 |
| 최댓값 | 12.0 |
| 평균 | ~7.80 |

### 4.4 응답 변수 범위

| 변수 | 범위 |
|------|------|
| S\_v (비표면적) | ~770 ~ 4491 m^-1 |
| K (투과도) | ~7.28 x 10^-9 ~ 4.87 x 10^-7 m^2 |

### 4.5 FAIL 분석

15개 FAIL 점은 다수가 \|t\| ~ 0.5 근처에 집중되어 있다. 이는 등가면 파라미터가 극단값에 가까울 때 공극률이 매우 낮거나 높아져 솔버 수렴 실패 또는 비물리적 결과를 생성하기 때문이다.

---

## 5. Phase 1b: Pareto + Top-5

### 5.1 Pareto 전면

Pareto 분석 결과 총 **50점**이 Pareto 전면에 위치하였다. 이는 계획서 기준(">=15점")을 대폭 초과하는 결과이다.

- **결과 파일**: `pareto_front.csv`
- **시각화**: `pareto_plot.png`, `pareto_params.png`

### 5.2 Top-5 설계 선정

Pareto 전면에서 다양한 설계 기준을 적용하여 5개 대표 설계(A~E)를 선정하였다.

| 설계 | a [mm] | t | epsilon | S\_v [m^-1] | K [m^2] | dP\_darcy [Pa] | 선정 기준 |
|------|--------|-------|---------|------------|---------|---------------|-----------|
| **A** | 3.00 | 0.433 | 0.359 | 4490.8 | 7.28 x 10^-9 | 100.19 | S\_v 극대 |
| **B** | 12.00 | -0.449 | 0.644 | 770.4 | 4.79 x 10^-7 | 1.52 | Delta-P 최소 |
| **C** | 3.70 | -0.082 | 0.526 | 2632.2 | 3.13 x 10^-8 | 23.30 | TOPSIS 균형 |
| **D** | 3.00 | 0.107 | 0.465 | 3568.4 | 1.47 x 10^-8 | 49.61 | epsilon~0.5 중 S\_v |
| **E** | 5.17 | 0.183 | 0.441 | 2252.4 | 3.65 x 10^-8 | 19.99 | a~5-6 제조성 |

- **결과 파일**: `top5_selected.csv`

### 5.3 선정 근거 상세

- **설계 A**: 비표면적(S\_v) 극대화를 위한 설계. a=3.0 mm의 최소 단위셀에서 높은 t값으로 좁은 채널을 형성하여 S\_v=4490.8 m^-1을 달성하나, 압력강하가 100.19 Pa로 가장 크다.
- **설계 B**: 압력강하 최소화 설계. a=12.0 mm의 최대 단위셀에서 넓은 유로를 형성하여 dP=1.52 Pa에 불과하나, S\_v=770.4 m^-1으로 비표면적은 최저이다.
- **설계 C**: TOPSIS 다기준 의사결정법 기반 균형 설계. 비표면적과 압력강하 모두 중간 수준으로 가장 실용적인 타협점을 제시한다.
- **설계 D**: 공극률 epsilon~0.5 부근에서 비표면적이 가장 높은 설계.
- **설계 E**: 단위셀 크기 a~5-6 mm 범위에서 제조성이 양호한 설계.

---

## 6. Phase 2: GHSV 감도

### 6.1 실험 설정

5개 Top-5 설계에 대해 각각 5가지 GHSV 조건을 적용하여 총 **25행**의 감도 분석을 수행하였다.

| GHSV [h^-1] | u\_in [m/s] |
|-------------|------------|
| 5,000 | 0.139 |
| 10,000 | 0.278 |
| 20,000 | 0.556 |
| 40,000 | 1.111 |
| 60,000 | 1.667 |

### 6.2 dP\_darcy 결과 [Pa]

| 설계 | GHSV 5000 | GHSV 10000 | GHSV 20000 | GHSV 40000 | GHSV 60000 |
|------|-----------|-----------|-----------|-----------|-----------|
| **A** | 50.1 | 100.3 | 200.5 | 400.7 | 601.2 |
| **B** | 0.76 | 1.52 | 3.05 | 6.09 | 9.14 |
| **C** | 11.7 | 23.3 | 46.6 | 93.2 | 139.8 |
| **D** | 24.8 | 49.6 | 99.3 | 198.4 | 297.7 |
| **E** | 10.0 | 20.0 | 40.0 | 79.9 | 119.9 |

- **결과 파일**: `ghsv_sensitivity.csv`

### 6.3 감도 분석 해석

- 모든 설계에서 dP는 GHSV(즉, 유입 속도)에 거의 **선형 비례**하며, Darcy 영역 내에서 동작함을 확인한다.
- 설계 A는 GHSV 60,000 h^-1에서 601.2 Pa에 달하여 실제 촉매 응용 시 펌핑 비용이 높아질 수 있다.
- 설계 B는 전 GHSV 범위에서 10 Pa 미만으로 압력강하가 매우 낮다.
- 설계 C와 E는 유사한 수준의 압력강하를 보이며, 실용 범위에 적합하다.

---

## 7. Phase 3: Forchheimer

### 7.1 이론 배경

Forchheimer 방정식은 다공질 매체를 통과하는 유동의 비선형 압력강하를 기술한다:

```
(Delta-P / L) / u = mu / K + beta * rho * u
```

여기서 좌변을 종속변수, u를 독립변수로 하는 **선형 회귀**를 통해 K\_darcy(Darcy 투과도)와 beta(Forchheimer 계수)를 추출한다.

### 7.2 회귀 결과

| 설계 | K\_darcy [m^2] | beta [m^-1] | R^2 | Re\_transition |
|------|---------------|------------|-----|---------------|
| **A** | 7.290 x 10^-9 | 2303.6 | 0.966 | 1.07 x 10^-4 |
| **B** | 5.809 x 10^-7 | 1.06 x 10^-11 | 0.373 | 3.85 x 10^9 (비물리) |
| **C** | 3.178 x 10^-8 | 2048.1 | 0.974 | 7.04 x 10^-5 |
| **D** | 1.477 x 10^-8 | 2145.2 | 0.965 | 9.23 x 10^-5 |
| **E** | 3.730 x 10^-8 | 2893.5 | 0.981 | 4.23 x 10^-5 |

- **결과 파일**: `forchheimer.csv`, `forchheimer_fit.csv`

### 7.3 설계 B 이슈 상세

설계 B에서 g\_lbm = 5 x 10^-4 및 2 x 10^-3 조건에서 **Ma > 0.1**이 발생하여 수치 발산이 일어났다. 이로 인해:

- beta = 1.06 x 10^-11 m^-1 (비물리적으로 작은 값)
- R^2 = 0.373 (비신뢰)
- Re\_transition = 3.85 x 10^9 (비물리적)

**권고 사항**: 논문 작성 시 설계 B의 고 g\_lbm 데이터 포인트를 제외하고, Darcy 영역 데이터만으로 K를 보고할 것을 권고한다.

### 7.4 R^2 평가

- 설계 E가 R^2 = 0.981로 가장 높으며 0.99에 근접한다.
- 설계 A, C, D는 R^2 0.96대로, 계획서 기준(>0.99)에는 미달하나 물리적 유효 속도 구간을 재한정하면 개선 가능하다.
- 설계 B는 R^2 = 0.373으로 실패.

---

## 8. Phase 4: 유동 특성화

### 8.1 유동 지표 결과

| 설계 | mixing\_ratio | uniformity | tortuosity tau | Re\_pore |
|------|-------------|-----------|---------------|---------|
| **A** | 0.814 | 0.694 | 1.302 | 6.46 x 10^-4 |
| **B** | 0.597 | 0.753 | 1.183 | 0.258 |
| **C** | 0.701 | 0.665 | 1.234 | 4.76 x 10^-3 |
| **D** | 0.739 | 0.664 | 1.258 | 1.63 x 10^-3 |
| **E** | 0.754 | 0.720 | 1.265 | 6.55 x 10^-3 |

- **결과 파일**: `flow_metrics.csv`

### 8.2 시각화 파일

각 Top-5 설계에 대해 4종류의 PNG 단면 이미지가 생성되었다 (총 20개):

| 파일명 패턴 | 내용 |
|------------|------|
| `top5_{A-E}_vz_xy.png` | z방향 속도장 (xy 단면) |
| `top5_{A-E}_vtrans_xy.png` | 횡방향 속도장 (xy 단면) |
| `top5_{A-E}_omega_xy.png` | 와도장 (xy 단면) |
| `top5_{A-E}_flow.png` | 종합 유동 시각화 |

### 8.3 유동 지표 해석

- **혼합비(mixing\_ratio)**: 설계 A가 0.814로 가장 높아 좁은 채널에서 유체 혼합이 활발하다. 설계 B는 0.597로 가장 낮으며, 넓은 유로에서 혼합이 상대적으로 부족하다.
- **균일도(uniformity)**: 설계 B가 0.753으로 가장 높아 유동 분배가 균일하다. 설계 C, D는 0.66대로 가장 낮다.
- **토투오시티(tortuosity)**: 설계 A가 tau=1.302로 가장 높아 유로 경로가 가장 굴곡져 있다. 설계 B는 1.183으로 가장 직선적이다.
- **세공 레이놀즈수(Re\_pore)**: 설계 B가 0.258으로 가장 높고, 설계 A가 6.46 x 10^-4로 가장 낮아 완전한 Stokes 유동 영역이다.

---

## 9. Phase 5: 재현성

### 9.1 실험 설계

5개 대표 (a, t) 조합에 대해 각 3회 반복 시뮬레이션을 수행하여 투과도 K의 재현성을 검증하였다.

### 9.2 결과

| (a, t) | K\_mean [m^2] | K\_std | CV [%] |
|--------|-------------|-------|--------|
| (3.5, 0.1) | 2.009 x 10^-8 | 2.37 x 10^-23 | 1.18 x 10^-13 |
| (5.0, 0.0) | 4.800 x 10^-8 | 1.32 x 10^-22 | 2.75 x 10^-13 |
| (5.0, 0.3) | 2.639 x 10^-8 | 2.07 x 10^-23 | 7.83 x 10^-14 |
| (8.0, -0.3) | 1.936 x 10^-7 | 3.68 x 10^-22 | 1.90 x 10^-13 |
| (10.0, -0.2) | 2.474 x 10^-7 | 3.50 x 10^-22 | 1.41 x 10^-13 |

- **결과 파일**: `repeatability.csv`, `repeatability_summary.csv`

### 9.3 판정

모든 조합에서 **CV << 0.1%** (실질적으로 CV ~ 10^-13 ~ 10^-14 %)로, LBM 솔버가 결정론적(deterministic)으로 동작함을 확인하였다.

**판정: PASS**

K\_std가 10^-22 ~ 10^-23 수준인 것은 부동소수점 연산의 미세 차이(GPU 스레드 스케줄링 등)에 의한 것이며, 물리적으로 무의미한 수준이다.

---

## 10. Phase 6: 격자 보강

### 10.1 개요

BO 탐색에서 상대적으로 희소했던 설계 공간 영역을 보강하기 위한 추가 시뮬레이션을 수행하였다.

- **대상 영역**: a = 9~12 mm, t grid 희소 영역
- **시뮬레이션 수**: 22행 (BO 중복 제외)
- **결과 파일**: `grid_supplement.csv`

### 10.2 목적

응답면(response surface) 보강을 통해 대형 단위셀 영역의 S\_v-K 관계를 보다 정밀하게 파악하고, 논문의 Supplementary Data로 활용한다.

---

## 11. 계획서 §10 체크리스트 대조표

| # | 항목 | 기준 | 결과 | 판정 |
|---|------|------|------|------|
| 1 | BO 100회 | 행 >= 100 | 100 | PASS |
| 2 | a 분포 3~12 | 골고루 분포 | min=3, max=12, mean~7.8 | PASS |
| 3 | Pareto 점 수 | >= 15 | 50 | PASS |
| 4 | Top-C != Top-B | 다름 | C(a=3.70, t=-0.082) != B(a=12.00, t=-0.449) | PASS |
| 5 | Forchheimer R^2 | > 0.99 | E 근접(0.981), A/C/D 0.96대, B 실패 | PARTIAL |
| 6 | 재현성 CV | < 0.1% | CV << 0.1% (10^-13 수준) | PASS |
| 7 | 고Re Ma | < 0.1 | B 고 g\_lbm에서 위반 및 발산 | PARTIAL |
| 8 | PNG 생성 | top5\_\* 존재 | 20개 PNG 생성 완료 | PASS |
| 9 | Reference 비교점 | pareto\_plot 존재 | 시각화 파일 존재 | PASS |
| 10 | 로그 오류 없이 완료 | "전체 완료" | `overnight.txt`에서 확인 | PASS |

### 미충족 항목 상세

- **#5 (Forchheimer R^2 > 0.99)**: 설계 E가 0.981로 가장 근접하나 미달. 설계 A, C, D는 0.96대. 물리적 유효 속도 구간을 재한정하여 재계산하면 개선 가능성 있음. 설계 B는 수치 발산으로 인한 R^2=0.373 실패.
- **#7 (고Re Ma < 0.1)**: 설계 B에서 g\_lbm = 5 x 10^-4, 2 x 10^-3 조건에서 Ma > 0.1 위반. 이는 대형 단위셀(a=12 mm)에서 높은 체적력 적용 시 발생하는 것으로, Ma 사전 스크리닝 로직이 필요하다.

---

## 12. 논문 매핑

### 12.1 본문 테이블 매핑

| 논문 위치 | 데이터 소스 | 내용 |
|----------|-----------|------|
| Table 1 | LBM 솔버 설정 | D3Q19 MRT, dx=0.2 mm, NX=NY=131 등 |
| Table 2 | BO 설정 | a 범위, t 범위, kappa, n\_init, n\_iter 등 |
| Table 3 | `top5_selected.csv` | Top-5 설계 요약 (a, t, epsilon, S\_v, K, dP) |
| Table 4 | `ghsv_sensitivity.csv` | GHSV별 dP 결과 |
| Table 5 | `forchheimer_fit.csv` | Forchheimer 회귀 계수 (K\_darcy, beta, R^2) |
| Table 6 | `flow_metrics.csv` | 유동 특성 지표 (mixing, uniformity, tau, Re) |

### 12.2 본문 그림 매핑

| 논문 위치 | 데이터 소스 | 내용 |
|----------|-----------|------|
| Fig. 1 | Gyroid 단위셀 3D 렌더링 | Gyroid 기하 구조 시각화 |
| Fig. 2 | `bo_results_v2.csv` | BO 수렴 이력 |
| Fig. 3 | `pareto_front.csv` + `pareto_plot.png` | Pareto front |
| Fig. 4 | `top5_{A-E}_vz_xy.png` | 속도장 단면 |
| Fig. 5 | `top5_{A-E}_omega_xy.png` | 와도장 단면 |

### 12.3 Supplementary 매핑

| 논문 위치 | 데이터 소스 |
|----------|-----------|
| Supplementary | `grid_supplement.csv` |
| Supplementary | `pareto_params.png` |
| Supplementary | `top5_{A-E}_vtrans_xy.png` |
| Supplementary | `top5_{A-E}_flow.png` |
| §4.3 (1문단, 재현성) | `repeatability_summary.csv` |

---

## 13. 한계 및 후속 과제

### 13.1 Forchheimer 고 g\_lbm에서의 Ma 초과 문제

- **현상**: 설계 B(a=12 mm)에서 g\_lbm = 5 x 10^-4 및 2 x 10^-3 조건에서 Ma > 0.1이 발생하여 수치 발산
- **영향**: R^2 = 0.373으로 비신뢰, beta 및 Re\_transition 비물리적
- **후속 과제**: g\_lbm 적용 전 Ma 사전 스크리닝 로직을 솔버에 내장하여, Ma > 0.1 예상 시 자동으로 g\_lbm을 하향 조정하는 기능 추가 필요

### 13.2 FAIL 15점 원인 분류 미완

- **현상**: BO 100회 중 15점이 FAIL이며, 대다수 \|t\| ~ 0.5 근방에 집중
- **후속 과제**: FAIL 원인을 코드 수준에서 체계적으로 분류(수렴 실패, 비물리적 공극률, 메시 해상도 부족 등)하는 후처리 스크립트 개발

### 13.3 VTK 출력 미구현

- **현상**: Plan 3.1V에서는 CSV + PNG 중심의 데이터 파이프라인으로 운영
- **후속 과제**: 3D 유동장의 상세 가시화가 필요한 경우, `run_flow_metrics.py`를 확장하여 VTK/VTI 포맷 출력을 추가

### 13.4 R^2 0.99 기준 미달

- **현상**: 최고 R^2 = 0.981 (설계 E), 나머지 A/C/D는 0.96대
- **후속 과제**: 물리적 유효 속도 구간을 제한하여(예: Ma < 0.05 조건만) Forchheimer 회귀를 재계산하면 R^2 개선 가능. 후속 캠페인에서 속도 구간 제한 재계산 권장.

---

## 14. 부록: 전체 파일 경로 인벤토리

### 14.1 결과 데이터 (results/campaign_plan31v/)

| 파일명 | 내용 | 비고 |
|--------|------|------|
| `bo_results_v2.csv` | BO 100회 전체 결과 | Phase 1 |
| `pareto_front.csv` | Pareto 전면 50점 | Phase 1b |
| `top5_selected.csv` | Top-5 설계 상세 | Phase 1b |
| `ghsv_sensitivity.csv` | GHSV 감도 25행 | Phase 2 |
| `forchheimer.csv` | Forchheimer 원시 데이터 25행 | Phase 3 |
| `forchheimer_fit.csv` | Forchheimer 회귀 결과 | Phase 3 |
| `flow_metrics.csv` | 유동 특성화 지표 | Phase 4 |
| `repeatability.csv` | 재현성 원시 데이터 (5점 x 3회) | Phase 5 |
| `repeatability_summary.csv` | 재현성 요약 (K\_mean, K\_std, CV) | Phase 5 |
| `grid_supplement.csv` | 격자 보강 22행 | Phase 6 |

### 14.2 시각화 (results/campaign_plan31v/)

| 파일명 | 내용 |
|--------|------|
| `pareto_plot.png` | Pareto front 시각화 |
| `pareto_params.png` | Pareto 파라미터 분포 시각화 |
| `top5_A_vz_xy.png` | 설계 A z-속도장 단면 |
| `top5_A_vtrans_xy.png` | 설계 A 횡방향 속도장 단면 |
| `top5_A_omega_xy.png` | 설계 A 와도장 단면 |
| `top5_A_flow.png` | 설계 A 종합 유동 시각화 |
| `top5_B_vz_xy.png` | 설계 B z-속도장 단면 |
| `top5_B_vtrans_xy.png` | 설계 B 횡방향 속도장 단면 |
| `top5_B_omega_xy.png` | 설계 B 와도장 단면 |
| `top5_B_flow.png` | 설계 B 종합 유동 시각화 |
| `top5_C_vz_xy.png` | 설계 C z-속도장 단면 |
| `top5_C_vtrans_xy.png` | 설계 C 횡방향 속도장 단면 |
| `top5_C_omega_xy.png` | 설계 C 와도장 단면 |
| `top5_C_flow.png` | 설계 C 종합 유동 시각화 |
| `top5_D_vz_xy.png` | 설계 D z-속도장 단면 |
| `top5_D_vtrans_xy.png` | 설계 D 횡방향 속도장 단면 |
| `top5_D_omega_xy.png` | 설계 D 와도장 단면 |
| `top5_D_flow.png` | 설계 D 종합 유동 시각화 |
| `top5_E_vz_xy.png` | 설계 E z-속도장 단면 |
| `top5_E_vtrans_xy.png` | 설계 E 횡방향 속도장 단면 |
| `top5_E_omega_xy.png` | 설계 E 와도장 단면 |
| `top5_E_flow.png` | 설계 E 종합 유동 시각화 |

### 14.3 로그 (logs/plan31v/)

| 파일명 | 내용 |
|--------|------|
| `overnight.txt` | 야간 오케스트레이션 메인 로그 |
| `phase*.txt` (8개) | 각 Phase별 상세 로그 |

---

> **본 문서는 Plan 3.1V 시뮬레이션 캠페인의 최종 종합분석보고서이며, 데이터 동결 시점은 2026-03-20이다. 이후 추가 분석이나 데이터 변경 시 별도의 개정판(revision)으로 관리한다.**

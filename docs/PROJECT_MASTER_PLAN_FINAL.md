# taichi_lbm_ref_gyroid — 리포지토리 구조화 · 최종보고서 · JKCS 논문 통합 수행계획서

**문서 버전:** v1.0 (2026-03-20)
**프로젝트 루트:** `/mnt/h/taichi_lbm_ref_gyroid/`
**대상 저널:** 한국세라믹학회지 (Journal of the Korean Ceramic Society, JKCS)
**제외 범위:** `geometry_exchange_ansys/` (본 계획 대상에서 제외)

---

## 0. 현황 진단

### 0.1 프로젝트 규모

| 항목 | 수량 | 비고 |
|------|------|------|
| Python 소스 (루트) | 11 | `solver_gyroid.py`, `bc_pressure.py`, `lattice_d3q19.py` 등 레거시 엔트리 |
| Python 소스 (solver/) | 2 | `__init__.py`, `taichi_lbm_core.py` (D3Q19 MRT 핵심) |
| Python 소스 (scripts/) | 31 | BO·Pareto·GHSV·Forchheimer·재현성·격자보강 파이프라인 |
| Shell 스크립트 | 3 | `run_overnight.sh`, `scripts/run_batch_plan21v.sh`, `scripts/run_plan22v_verify.sh` |
| MD 문서 (docs/) | 76 | plan 시리즈·결과보고서·검증·실행지시서 |
| MD 문서 (루트) | 2 | `README.md`, `docs_Taichi_LBM_ref_gyroid_report.md` |
| CSV 결과 | 20 | `results/*.csv` + `Results_*/simulation_log.csv` |
| VTR 시각화 | 15 | `results/*.vtr`, `results/l2a_vti/` |
| PNG 이미지 | 40 | `results/top5_*`, `pareto_*`, `plan23v_vis/` 등 |
| NPY 대용량 | 4 | 루트 `verify_duct_*.npy` (33~35 MB), `vz_outlet_l2_131.npy` |
| 로그 파일 | 42 | 루트 10, `logs/` 32 |
| geometry_openscad/ | 9 | STL 4, SCAD 2, NPY 1, PY 1, MD 1 |
| Git 상태 | — | **git 미초기화**, `.gitignore` 없음 |

### 0.2 핵심 문제

1. **루트 혼재** — 레거시 Python 11개, 로그 10개, NPY 4개, PNG 2개가 루트에 산재
2. **docs/ 76개 파일** — plan·보고서·검증·지시서가 flat 구조로 혼합
3. **Results_* 5개 폴더** — 검증용 레거시 결과가 루트 최상위에 노출
4. **Git 부재** — `.gitignore`, 커밋 이력 없음
5. **LaTeX 부재** — JKCS 투고용 논문 빌드 체계 전무

---

## Phase A — 폴더 구조 재설계

### A.1 목표 트리

```text
taichi_lbm_ref_gyroid/
├── README.md                          # 프로젝트 개요 (갱신)
├── requirements.txt                   # 의존성 (버전 고정)
├── .gitignore                         # 신규 생성
├── run_overnight.sh                   # 야간 파이프라인 (경로 갱신)
│
├── solver/                            # [유지] LBM 핵심 모듈
│   ├── __init__.py
│   └── taichi_lbm_core.py            #   D3Q19 MRT-LBM
│
├── scripts/                           # [유지] 실행·분석 스크립트 31개
│   ├── run_bo_pipeline.py
│   ├── analyze_pareto.py
│   ├── run_ghsv_sensitivity.py
│   ├── run_forchheimer.py
│   ├── run_flow_metrics.py
│   ├── run_repeatability.py
│   ├── run_grid_supplement.py
│   └── ...
│
├── legacy/                            # [신규] 루트 레거시 Python 이관
│   ├── solver_gyroid.py
│   ├── solver_reference.py
│   ├── bc_pressure.py
│   ├── lattice_d3q19.py
│   ├── geometry_io.py
│   ├── postprocess.py
│   ├── unit_converter.py
│   ├── validation_criteria.py
│   ├── compare_taichi_openlb.py
│   ├── convert_gate_a_dat_to_npy.py
│   └── convert_verify_duct_to_mask.py
│
├── results/                           # [재구성] 캠페인별 분류
│   ├── campaign_plan31v/              #   plan 3.1V 핵심 산출물
│   │   ├── bo_results_v2.csv
│   │   ├── pareto_front.csv
│   │   ├── top5_selected.csv
│   │   ├── ghsv_sensitivity.csv
│   │   ├── forchheimer.csv
│   │   ├── forchheimer_fit.csv
│   │   ├── flow_metrics.csv
│   │   ├── repeatability.csv
│   │   ├── repeatability_summary.csv
│   │   ├── grid_supplement.csv
│   │   ├── pareto_plot.png
│   │   ├── pareto_params.png
│   │   └── top5_*.png (20개)
│   ├── campaign_legacy/               #   이전 캠페인 결과
│   │   ├── bo_results.csv
│   │   ├── bo_smoke*.csv
│   │   ├── top3_summary.csv
│   │   ├── top3_*.vtr (3개)
│   │   ├── top3_*.png (6개)
│   │   ├── gyroid_diag_*.vtr (7개)
│   │   ├── gyroid_*.png (4개)
│   │   └── plan23v_vis/ (5 PNG)
│   ├── l2a_vti/                       #   L2A VTR 진단 데이터 (유지)
│   └── README.md
│
├── logs/                              # [재구성] 시기별 분류
│   ├── plan31v/                       #   야간 파이프라인 로그
│   │   ├── overnight.txt
│   │   ├── phase1_bo.txt
│   │   ├── phase1b_pareto.txt
│   │   ├── phase2_ghsv.txt
│   │   ├── phase3_forch.txt
│   │   ├── phase4_flow.txt
│   │   ├── phase5_repeat.txt
│   │   └── phase6_grid.txt
│   ├── legacy/                        #   루트·이전 로그 이관
│   │   ├── log_duct_200C.txt
│   │   ├── log_duct_200C_v2.txt
│   │   ├── log_duct_v3.txt
│   │   ├── log_ref_dx02.txt
│   │   ├── batch_log.txt
│   │   ├── run_l*_log.txt (5개)
│   │   └── plan22v_verify.log
│   └── analysis/                      #   기존 logs/ 내 분석 로그
│       ├── bo_full.txt, bo_smoke.txt
│       ├── gci_short*.txt (3개)
│       ├── gyroid_3g*.txt (5개)
│       ├── diag_connectivity*.txt (2개)
│       ├── vti_*.txt (다수)
│       └── batch_20260318_*/, plan22v_20260318_*/
│
├── archive/                           # [신규] 검증용 레거시 + 대용량
│   ├── Results_EmptyDuct_200C/
│   ├── Results_EmptyDuct_200C_v2/
│   ├── Results_EmptyDuct_Taichi/
│   ├── Results_EmptyDuct_v3/
│   ├── Results_Ref_dx02/
│   ├── verify_duct_25.4mm_mask.npy    #   33.5 MB
│   ├── verify_duct_nowall_mask.npy    #   34.9 MB
│   ├── vz_outlet_l2_131.npy
│   ├── gyroid_wall_mask.png
│   └── verify_empty_duct_mask.png
│
├── docs/                              # [재구성] 유형별 하위 분류
│   ├── plans/                         #   계획서 원본 (plan_*.md 시리즈)
│   │   ├── plan_1.1V.md ~ plan_1.92V.md
│   │   ├── plan_2.1V_종합결과보고서.md ~ plan_2.6V.md
│   │   ├── plan_3.0V.md, plan_3.1V.md
│   │   ├── plan_v1.6V.md
│   │   └── [mainplan]_V1.1.md
│   ├── reports/                       #   결과보고서·분석보고서
│   │   ├── FINAL_종합분석보고서_plan31v.md    # ← Phase C 최종본
│   │   ├── plan_3.1V_실행결과_상세종합분석보고서.md  # 기존 베이스
│   │   ├── L2_결과_상세분석_보고서.md
│   │   ├── 실행결과종합분석보고서.md
│   │   ├── 종합_상세분석_결과보고서.md
│   │   ├── 종합분석보고서V1.md, 종합분석보고서_V3.md
│   │   ├── plan_*_결과보고서.md (다수)
│   │   └── docs_Taichi_LBM_ref_gyroid_report.md  # 루트에서 이관
│   ├── verification/                  #   검증·격자독립성 문서
│   │   ├── 검증_L1_빈덕트_판정.md
│   │   ├── 검증_MRT_BGK_확인.md
│   │   ├── 검증_Reference_6x6_현황.md
│   │   ├── 검증_형상_3종_STL_및_파이프라인.md
│   │   ├── 격자독립성_GCI_*.md (2개)
│   │   └── 벽두께_검증_절차_3격자이상.md
│   ├── instructions/                  #   실행지시서·절차
│   │   ├── 실행지시서_*.md (다수)
│   │   └── 코드구조_대응표.md
│   ├── theory/                        #   이론·수식 검증
│   │   ├── Taichi_커널_자이로이드_수식_검증.md
│   │   ├── 지오메트리_수식_정립.md
│   │   └── 후처리_정의_ΔP_Sv_CV_Ma.md
│   └── PROJECT_MASTER_PLAN_FINAL.md   #   본 문서
│
├── paper/                             # [신규] JKCS 논문 프로젝트
│   └── jkcs/
│       ├── main.tex
│       ├── sections/
│       │   ├── 01_introduction.tex
│       │   ├── 02_methods.tex
│       │   ├── 03_results.tex
│       │   ├── 04_discussion.tex
│       │   └── 05_conclusion.tex
│       ├── figures/                   #   논문용 Figure (results에서 복사·고정)
│       ├── tables/                    #   LaTeX 표 소스
│       ├── references.bib
│       ├── Makefile / latexmkrc
│       └── COMPLIANCE.md              #   저널 투고 체크리스트
│
├── geometry_openscad/                 # [유지] OpenSCAD 기하 정의
│   ├── README.md
│   ├── empty_duct_v32.scad, .stl
│   ├── reference_6x6_v32.scad, .stl
│   ├── gyroid_duct_v32_final.stl
│   ├── gyroid_taichi_formula.stl, .py
│   └── gyroid_duct_v32_formula.npy
│
└── .venv_v32/                         # [유지] 가상환경 (git 제외)
```

### A.2 분류 규칙

| 대상 파일/폴더 | 현재 위치 | 이동 대상 | 판단 근거 |
|----------------|-----------|-----------|-----------|
| `solver_gyroid.py` 외 루트 Python 11개 | `/` (루트) | `legacy/` | `solver/`·`scripts/`에서 import하지 않는 독립 레거시 |
| `Results_EmptyDuct_*` (4개), `Results_Ref_dx02` | `/` (루트) | `archive/` | 검증 완료된 과거 캠페인 |
| `verify_duct_*.npy`, `vz_outlet_l2_131.npy` | `/` (루트) | `archive/` | 대용량 바이너리, 논문 직접 인용 없음 |
| `gyroid_wall_mask.png`, `verify_empty_duct_mask.png` | `/` (루트) | `archive/` | 검증용 이미지 |
| `log_*.txt`, `batch_log.txt`, `run_l*_log.txt`, `plan22v_verify.log` | `/` (루트) | `logs/legacy/` | 루트 산재 로그 정리 |
| `docs_Taichi_LBM_ref_gyroid_report.md` | `/` (루트) | `docs/reports/` | 문서는 docs 내 보관 |
| `overnight.txt`, `phase*.txt` | `logs/` | `logs/plan31v/` | plan 3.1V 야간 파이프라인 로그 |
| `bo_results_v2.csv` 외 plan31v 산출물 | `results/` | `results/campaign_plan31v/` | 현행 캠페인 고정 |
| `bo_results.csv`, `bo_smoke*.csv`, `top3_*` | `results/` | `results/campaign_legacy/` | 이전 캠페인 분리 |
| plan_*.md (계획 시리즈) | `docs/` | `docs/plans/` | 유형별 분류 |
| *보고서*.md, *결과*.md | `docs/` | `docs/reports/` | 유형별 분류 |
| 검증_*.md, 격자독립성_*.md | `docs/` | `docs/verification/` | 유형별 분류 |
| 실행지시서_*.md | `docs/` | `docs/instructions/` | 유형별 분류 |
| 수식·이론 관련 | `docs/` | `docs/theory/` | 유형별 분류 |

### A.3 `.gitignore` 생성 내용

```gitignore
# Python
__pycache__/
*.pyc
.venv_v32/

# 대용량 바이너리
archive/*.npy
*.npy

# 빌드 산출물
paper/jkcs/*.aux
paper/jkcs/*.log
paper/jkcs/*.out
paper/jkcs/*.bbl
paper/jkcs/*.blg
paper/jkcs/*.fls
paper/jkcs/*.fdb_latexmk
paper/jkcs/*.synctex.gz
paper/jkcs/*.pdf

# OS
.DS_Store
Thumbs.db

# 제외 범위
geometry_exchange_ansys/
```

### A.4 경로 변경 후 점검 항목

| 점검 대상 | 방법 | 승인 기준 |
|-----------|------|-----------|
| `run_overnight.sh` 내 경로 | `grep -n "results/"` → 새 경로로 수정 | 스크립트 dry-run PASS |
| `scripts/*.py`의 `argparse` 기본값 | 각 `--output` 인자 확인 | `python -m py_compile scripts/*.py` 전수 PASS |
| `solver/` import 체인 | `from solver import TaichiLBMCore` 테스트 | import 성공 |
| `README.md` 예시 경로 | 수동 검토 | 모든 경로 실존 확인 |

---

## Phase B — 결과·로그 최종 정리

### B.1 파일 인벤토리 작성

`docs/reports/file_inventory.md` 또는 JSON으로 다음 컬럼 기록:

| 컬럼 | 설명 |
|------|------|
| `path` | 이동 후 최종 경로 |
| `original_path` | 이동 전 원래 경로 |
| `size_kb` | 파일 크기 |
| `campaign` | `plan31v` / `legacy` / `validation` |
| `paper_mapping` | 논문 Table/Figure 번호 (해당 시) |
| `description` | 내용 한 줄 설명 |

### B.2 plan 3.1V 산출물 고정 목록

`results/campaign_plan31v/`로 이동할 **15개 핵심 파일**:

| # | 파일명 | 행 수 | 용도 |
|---|--------|-------|------|
| 1 | `bo_results_v2.csv` | 100 | BO 전체 결과 |
| 2 | `pareto_front.csv` | 50 | Pareto 최적 해 |
| 3 | `top5_selected.csv` | 5 | 대표 설계 A~E |
| 4 | `ghsv_sensitivity.csv` | 25 | GHSV 감도 (5설계×5조건) |
| 5 | `forchheimer.csv` | 25 | g_lbm 스윕 원시 |
| 6 | `forchheimer_fit.csv` | 5 | K_darcy·β·R² 회귀 |
| 7 | `flow_metrics.csv` | 5 | 유동 특성 지표 |
| 8 | `repeatability.csv` | 15 | 재현성 원시 (5점×3회) |
| 9 | `repeatability_summary.csv` | 5 | CV 요약 |
| 10 | `grid_supplement.csv` | 22 | 격자 보강 |
| 11 | `pareto_plot.png` | — | Pareto 전면 시각화 |
| 12 | `pareto_params.png` | — | 설계변수 분포 |
| 13~32 | `top5_{A~E}_{vz_xy,vtrans_xy,omega_xy,flow}.png` | — | 유동장 시각화 20장 |

### B.3 레거시 격리 대상

`results/campaign_legacy/`로 이동: `bo_results.csv`, `bo_smoke.csv`, `bo_smoke_p30.csv`, `bo_smoke_v2.csv`, `top3_summary.csv`, `top3_{A,B,C}.vtr`, `top3_*_*.png`(6장), `gyroid_diag_*.vtr`(7개), `gyroid_*.png`(4장), `plan23v_vis/`(5 PNG)

### B.4 재현성 확보 기록

`requirements.txt`를 **버전 고정**으로 갱신:

```text
taichi==1.7.4
numpy>=1.24.0
scikit-optimize>=0.9.0
matplotlib>=3.7.0
pyvista>=0.42.0
```

환경 메타데이터 (보고서에 기재):
- Python 3.13.2, Taichi 1.7.4, arch=cuda
- 가상환경: `.venv_v32`
- 실행 일시: 2026-03-19 22:13 ~ 2026-03-20 02:34 KST (약 4.2시간)

---

## Phase C — 최종 종합 상세 분석 보고서 (단일 최종본)

### C.1 파일

`docs/reports/FINAL_종합분석보고서_plan31v.md`

### C.2 필수 목차 구성

```
1. 표지 (저자, 버전, 데이터 동결 날짜)
2. Executive Summary
3. 물리·기하 설정 표
4. 코드·스크립트 경로 표
5. Phase 1: BO 결과 (100회, 85 OK / 15 FAIL)
   5.1 설정 (a∈[3,12], t∈(-0.5,0.5), LCB kappa=3, n_init=20, n_iter=80)
   5.2 통계 요약 테이블
   5.3 FAIL 패턴 분석
6. Phase 1b: Pareto + Top-5
   6.1 Pareto 50점 규모
   6.2 Top-5 (A~E) 핵심 수치 테이블
   6.3 시각화 (pareto_plot.png 삽입)
7. Phase 2: GHSV 감도
   7.1 5조건 (5k~60k h⁻¹) × 5설계 = 25행
   7.2 Darcy ΔP 환산 테이블
8. Phase 3: Forchheimer
   8.1 이론 (ΔP/L)/u vs u 선형 회귀
   8.2 설계별 K_darcy, β, R² 테이블
   8.3 설계 B 한계 분석 (Ma>0.1 발산)
9. Phase 4: 유동 특성화
   9.1 mixing_ratio, uniformity, tortuosity, Re_pore 테이블
   9.2 단면 시각화 해석
10. Phase 5: 재현성
    10.1 5점×3회, CV ≪ 0.1% 정량 확인
11. Phase 6: 격자 보강
    11.1 22점 보강, 응답면 신뢰도 향상
12. 계획서 §10 체크리스트 대조표
13. 논문 매핑 (데이터→JKCS Table/Figure 1:1 대응)
14. 한계 및 후속 과제
15. 부록: 전체 파일 경로 인벤토리
```

### C.3 핵심 수치 테이블 (보고서 삽입용)

#### 테이블 1: Top-5 설계 요약

| 설계 | a [mm] | t | ε | S_v [m⁻¹] | K [m²] | dP_darcy [Pa] | 선정 기준 |
|------|--------|------|-------|----------|--------|--------------|-----------|
| **A** | 3.00 | 0.433 | 0.359 | 4490.8 | 7.28×10⁻⁹ | 100.19 | S_v 극대 |
| **B** | 12.00 | -0.449 | 0.644 | 770.4 | 4.79×10⁻⁷ | 1.52 | ΔP 최소 |
| **C** | 3.70 | -0.082 | 0.526 | 2632.2 | 3.13×10⁻⁸ | 23.30 | TOPSIS 균형 |
| **D** | 3.00 | 0.107 | 0.465 | 3568.4 | 1.47×10⁻⁸ | 49.61 | ε~0.5 중 S_v |
| **E** | 5.17 | 0.183 | 0.441 | 2252.4 | 3.65×10⁻⁸ | 19.99 | a~5–6 제조성 |

#### 테이블 2: Forchheimer 회귀

| 설계 | K_darcy [m²] | β [m⁻¹] | R² | 논문 보고 |
|------|-------------|---------|-----|----------|
| A | 7.29×10⁻⁹ | 2.30×10³ | 0.966 | 가능 |
| B | 5.81×10⁻⁷ | ~10⁻¹¹ | 0.373 | **제외** (Ma>0.1 발산) |
| C | 3.18×10⁻⁸ | 2.05×10³ | 0.974 | 가능 |
| D | 1.48×10⁻⁸ | 2.15×10³ | 0.965 | 가능 |
| E | 3.73×10⁻⁸ | 2.89×10³ | 0.981 | 가능 |

#### 테이블 3: 유동 특성

| 설계 | mixing_ratio | uniformity | tortuosity τ | Re_pore |
|------|-------------|-----------|-------------|---------|
| A | 0.814 | 0.694 | 1.302 | 6.5×10⁻⁴ |
| B | 0.597 | 0.753 | 1.183 | 0.258 |
| C | 0.701 | 0.665 | 1.234 | 4.8×10⁻³ |
| D | 0.739 | 0.664 | 1.258 | 1.6×10⁻³ |
| E | 0.754 | 0.720 | 1.265 | 6.5×10⁻³ |

#### 테이블 4: 재현성

| (a, t) | K_mean [m²] | CV [%] | 판정 |
|--------|-------------|--------|------|
| (3.5, 0.1) | 2.01×10⁻⁸ | ~10⁻¹¹ | PASS |
| (5.0, 0.0) | 4.80×10⁻⁸ | ~10⁻¹³ | PASS |
| (5.0, 0.3) | 2.64×10⁻⁸ | ~10⁻¹⁴ | PASS |
| (8.0, -0.3) | 1.94×10⁻⁷ | ~10⁻¹³ | PASS |
| (10.0, -0.2) | 2.47×10⁻⁷ | ~10⁻¹³ | PASS |

### C.4 코드·스크립트 절대경로 표 (보고서 삽입용)

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

### C.5 기존 보고서 처리

- `docs/plan_3.1V_실행결과_상세종합분석보고서.md` → `docs/reports/`로 이동
- 최종본(`FINAL_종합분석보고서_plan31v.md`)의 §1에 "본 문서는 기존 `plan_3.1V_실행결과_상세종합분석보고서.md`를 흡수·확장한 최종본" 명시
- 기존 보고서 상단에 리다이렉트 안내 1줄 추가

---

## Phase D — JKCS 논문용 LaTeX 구축

### D.1 저널 정보

| 항목 | 내용 |
|------|------|
| 저널명 | Journal of the Korean Ceramic Society (한국세라믹학회지) |
| 출판사 | Springer (Korean Ceramic Society 발행) |
| 홈페이지 | https://www.jkcs.or.kr/ |
| 투고 안내 | https://www.springer.com/journal/43207/submission-guidelines |
| E-Submission | https://www.editorialmanager.com/jkcs/default.aspx |
| 본문 언어 | 영문 (English only) |
| 템플릿 | Springer LaTeX template (sn-jnl 클래스) |

### D.2 논문 구조 및 데이터 매핑

```
Title: Bayesian Optimization of Gyroid TPMS Catalyst Support
       Geometry for Pressure Drop and Surface Area Using
       Lattice Boltzmann Method

Abstract: (~250 words)
Keywords: Gyroid, TPMS, Lattice Boltzmann, Bayesian optimization,
          catalyst support, permeability
```

#### 섹션별 구성 및 Figure/Table 매핑

| 섹션 | 내용 | 데이터 소스 | 논문 Table/Figure |
|------|------|------------|-------------------|
| **1. Introduction** | 세라믹 촉매 지지체, TPMS/Gyroid 동기, LBM 적용 배경 | 문헌 | — |
| **2. Methods** | | | |
| 2.1 Gyroid geometry | 단위셀 정의, (a, t) 파라미터, ε·S_v 계산 | `solver/taichi_lbm_core.py`, `scripts/init_gyroid_mask_v32.py` | **Fig. 1**: Gyroid 단위셀 3D |
| 2.2 LBM solver | D3Q19 MRT, body force, 주기 BC, 수렴 기준 | `solver/taichi_lbm_core.py` | **Table 1**: LBM 파라미터 (NX, NY, dx, ν 등) |
| 2.3 BO framework | `gp_minimize`, LCB, kappa=3, a∈[3,12], n=100 | `scripts/run_bo_pipeline.py` | **Table 2**: BO 설정 |
| 2.4 Post-processing | K, ΔP, S_v, Forchheimer, tortuosity 정의 | `scripts/run_forchheimer.py` 등 | — |
| **3. Results** | | | |
| 3.1 BO convergence | 100회 탐색, 85 OK / 15 FAIL | `bo_results_v2.csv` | **Fig. 2**: BO 수렴 이력 |
| 3.2 Pareto front | S_v vs ΔP 트레이드오프, 50점 | `pareto_front.csv` | **Fig. 3**: Pareto plot (`pareto_plot.png`) |
| 3.3 Top-5 designs | A~E 선정, 핵심 수치 | `top5_selected.csv` | **Table 3**: Top-5 요약 (= 보고서 테이블 1) |
| 3.4 Flow visualization | 속도장·와도 단면 | `top5_*_{vz_xy,omega_xy}.png` | **Fig. 4–5**: 대표 설계 유동장 |
| 3.5 GHSV sensitivity | 5조건 ΔP 변화 | `ghsv_sensitivity.csv` | **Table 4**: GHSV별 ΔP |
| 3.6 Forchheimer | K_darcy, β, R² (B 제외) | `forchheimer_fit.csv` | **Table 5**: Forchheimer 회귀 |
| 3.7 Flow metrics | mixing, tortuosity | `flow_metrics.csv` | **Table 6**: 유동 특성 |
| **4. Discussion** | | | |
| 4.1 Design trade-offs | S_v↑ vs ΔP↑, 제조 가능성 | — | — |
| 4.2 Limitations | 설계 B Ma>0.1, R²<0.99 | `forchheimer_fit.csv` | — |
| 4.3 Reproducibility | CV ≪ 0.1% | `repeatability_summary.csv` | 본문 1문단 |
| **5. Conclusion** | 핵심 기여, 향후 과제 | — | — |
| **References** | | `references.bib` | — |

**예상 Figure 6~8장, Table 6~7개**

### D.3 LaTeX 프로젝트 구축 절차

| 단계 | 작업 | 산출물 |
|------|------|--------|
| D.3.1 | Springer JKCS LaTeX 템플릿(`sn-jnl.cls`) 다운로드 | `paper/jkcs/sn-jnl.cls`, `sn-*.bst` |
| D.3.2 | `main.tex` 작성, `\input{sections/0X_*.tex}` 구조 | `paper/jkcs/main.tex` |
| D.3.3 | Figure 복사: `results/campaign_plan31v/*.png` → `paper/jkcs/figures/` | 해상도·폰트 통일 (300 DPI, sans-serif) |
| D.3.4 | Table 변환: MD 표 → `booktabs` LaTeX 표 | `paper/jkcs/tables/*.tex` |
| D.3.5 | `references.bib` 초안 (LBM, Gyroid, BO 핵심 문헌 20~30편) | `paper/jkcs/references.bib` |
| D.3.6 | 빌드 테스트: `latexmk -pdf main.tex` | `main.pdf` |
| D.3.7 | `COMPLIANCE.md` 작성: 저널 체크리스트 | `paper/jkcs/COMPLIANCE.md` |

### D.4 JKCS 투고 체크리스트 (COMPLIANCE.md 내용)

| # | 항목 | 확인 |
|---|------|------|
| 1 | 본문 영문 작성 | ☐ |
| 2 | Abstract ≤ 250 words | ☐ |
| 3 | Keywords 4~6개 | ☐ |
| 4 | Figure 해상도 ≥ 300 DPI | ☐ |
| 5 | Table에 SI 단위 명시 | ☐ |
| 6 | Reference 스타일: Springer numbered | ☐ |
| 7 | Data Availability Statement 포함 | ☐ |
| 8 | Author contributions 명시 | ☐ |
| 9 | Conflict of interest 선언 | ☐ |
| 10 | Editorial Manager 제출 PDF + 소스 | ☐ |
| 11 | Graphical Abstract (필요 시) | ☐ |
| 12 | Supplementary material (필요 시) | ☐ |

---

## Phase E — 실행 절차 및 일정

### E.1 실행 순서

```
Phase A  →  Phase B  →  Phase C  →  Phase D
(구조화)    (정리)      (보고서)     (논문)
   │                       │
   └── A.4 점검 ──────────┘
```

### E.2 단계별 세부 작업

#### Phase A — 폴더 구조화

| # | 작업 | 상세 | 완료 기준 |
|---|------|------|-----------|
| A-1 | `.gitignore` 생성 | §A.3 내용 기록 | 파일 존재 |
| A-2 | `legacy/` 생성 + 루트 Python 11개 이동 | §A.2 규칙 적용 | `ls legacy/` = 11 파일 |
| A-3 | `archive/` 생성 + Results_* 5개 + NPY 3개 + PNG 2개 이동 | §A.2 규칙 | `ls archive/` = 10항목 |
| A-4 | `logs/plan31v/` 생성 + phase 로그 이동 | overnight.txt + phase*.txt = 8파일 | 확인 |
| A-5 | `logs/legacy/` 생성 + 루트 로그 10개 이동 | §A.2 규칙 | 확인 |
| A-6 | `logs/analysis/` 생성 + 기존 logs/ 내 분석 로그 재분류 | batch_*, gci_*, gyroid_* 등 | 확인 |
| A-7 | `results/campaign_plan31v/` 생성 + 핵심 15개 파일 이동 | §B.2 목록 | 확인 |
| A-8 | `results/campaign_legacy/` 생성 + 레거시 결과 이동 | §B.3 목록 | 확인 |
| A-9 | `docs/` 하위 5개 폴더 생성 + 76개 MD 재분류 | plans/, reports/, verification/, instructions/, theory/ | 각 폴더 파일 수 합계 = 76 |
| A-10 | 루트 `docs_*.md` → `docs/reports/` 이동 | 1파일 | 확인 |
| A-11 | `run_overnight.sh` 경로 수정 | `results/` → `results/campaign_plan31v/` | dry-run PASS |
| A-12 | `scripts/*.py` 출력 경로 점검·수정 | `grep -rn "results/"` | `py_compile` 전수 PASS |
| A-13 | `README.md` 갱신 | 새 트리 반영, 사용법 갱신 | 수동 검토 |
| A-14 | `paper/jkcs/` 디렉토리 생성 | sections/, figures/, tables/ 포함 | 구조 존재 |

#### Phase B — 결과·로그 정리

| # | 작업 | 완료 기준 |
|---|------|-----------|
| B-1 | `docs/reports/file_inventory.md` 작성 | 전체 파일 인벤토리 완성 |
| B-2 | `requirements.txt` 버전 고정 갱신 | §B.4 내용 반영 |
| B-3 | `results/README.md` 갱신 | campaign 구조 설명 |

#### Phase C — 최종 보고서

| # | 작업 | 완료 기준 |
|---|------|-----------|
| C-1 | `FINAL_종합분석보고서_plan31v.md` 초안 | §C.2 목차 전체 작성 |
| C-2 | 핵심 수치 테이블 4개 삽입 | §C.3 테이블 1~4 정확 기재 |
| C-3 | 코드 경로 표 삽입 | §C.4 전체 경로 실존 검증 |
| C-4 | 체크리스트 대조표 삽입 | plan_3.1V §10 항목 10개 대조 |
| C-5 | 논문 매핑 섹션 삽입 | §D.2 Table/Figure 매핑 동기화 |
| C-6 | 기존 보고서 리다이렉트 처리 | §C.5 절차 |

#### Phase D — LaTeX 구축

| # | 작업 | 완료 기준 |
|---|------|-----------|
| D-1 | Springer JKCS 템플릿 다운로드·배치 | `paper/jkcs/sn-jnl.cls` 존재 |
| D-2 | `main.tex` + 5개 section tex 생성 | 컴파일 가능 skeleton |
| D-3 | Figure 복사·해상도 검증 | `paper/jkcs/figures/` 에 6~8장 |
| D-4 | Table LaTeX 변환 | `paper/jkcs/tables/` 에 6~7개 |
| D-5 | `references.bib` 초안 | 핵심 문헌 20편 이상 |
| D-6 | `latexmk -pdf` 빌드 성공 | PDF 생성 확인 |
| D-7 | `COMPLIANCE.md` 작성 | §D.4 체크리스트 |

### E.3 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 경로 변경으로 스크립트 실패 | 파이프라인 중단 | A-12에서 `py_compile` + 스모크 1회 실행 |
| JKCS 템플릿 다운로드 불가 | LaTeX 빌드 불가 | Springer 일반 `sn-article` 클래스로 대체 |
| 기존 docs/ 분류 모호 파일 | 잘못된 폴더 배치 | 파일명·내용 1차 검토 후 분류, 모호한 것은 `docs/plans/`에 |
| Forchheimer R²<0.99 | 체크리스트 미충족 | 논문에서 "저Ma 서브셋 회귀" 또는 "설계 B 제외" 명시 |

---

## 부록: docs/ 76개 파일 분류 매핑 (참고)

### plans/ (계획서 원본)

`plan_1.1V.md`, `plan_1.2V.md`, `plan_1.3V.md`, `plan_1.4V.md`, `plan_1.5V.md`, `plan_v1.6V.md`, `plan_1.7V.md`, `plan_1.9V.md`, `plan_1.91V.md`, `plan_1.92V.md`, `plan_2.1V_종합결과보고서.md`, `plan_2.2V.md`, `plan_2.3V.md`, `plan_2.4V.md`, `plan_2.5V.md`, `plan_2.6V.md`, `plan_3.0V.md`, `plan_3.1V.md`, `[mainplan]_V1.1.md`

### reports/ (결과보고서)

`plan_3.1V_실행결과_상세종합분석보고서.md`, `L2_결과_상세분석_보고서.md`, `실행결과종합분석보고서.md`, `종합_상세분석_결과보고서.md`, `종합분석보고서V1.md`, `종합분석보고서_V3.md`, `geometry_exchange_ansys_종합분석보고서.md`, `plan_*_결과보고서.md` 시리즈, `FINAL_종합분석보고서_plan31v.md` (신규)

### verification/ (검증)

`검증_L1_빈덕트_판정.md`, `검증_MRT_BGK_확인.md`, `검증_Reference_6x6_현황.md`, `검증_형상_3종_STL_및_파이프라인.md`, `격자독립성_GCI_3level_계획.md`, `격자독립성_GCI_plan13v.md`, `벽두께_검증_절차_3격자이상.md`

### instructions/ (실행지시서·절차)

`실행지시서_*.md` 시리즈, `코드구조_대응표.md`

### theory/ (이론·수식)

`Taichi_커널_자이로이드_수식_검증.md`, `지오메트리_수식_정립.md`, `후처리_정의_ΔP_Sv_CV_Ma.md`

---

*본 계획서는 `/mnt/h/taichi_lbm_ref_gyroid/` 2026-03-20 시점의 파일 현황을 기반으로 작성되었다.*

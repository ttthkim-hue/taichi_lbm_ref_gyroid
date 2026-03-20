# Taichi LBM Reference & Gyroid Validation

Taichi 기반 D3Q19 MRT Lattice Boltzmann Method(LBM)으로
Gyroid TPMS 촉매 지지체의 투과도·압력손실을 시뮬레이션하고,
베이지안 최적화(BO)로 설계변수(a, t)를 탐색하는 프로젝트.

## 프로젝트 구조

```
taichi_lbm_ref_gyroid/
├── README.md                    # 현재 파일
├── requirements.txt             # 의존성 (taichi, numpy 등)
├── .gitignore
├── run_overnight.sh             # plan_3.1V 야간 파이프라인
│
├── solver/                      # LBM 핵심 모듈
│   ├── __init__.py
│   └── taichi_lbm_core.py       #   D3Q19 MRT-LBM 솔버
│
├── scripts/                     # 실행·분석 스크립트 (31개)
│   ├── run_bo_pipeline.py       #   BO 파이프라인
│   ├── analyze_pareto.py        #   Pareto + Top-5 선정
│   ├── run_ghsv_sensitivity.py  #   GHSV 감도 분석
│   ├── run_forchheimer.py       #   Forchheimer 회귀
│   ├── run_flow_metrics.py      #   유동 특성화
│   ├── run_repeatability.py     #   재현성 테스트
│   ├── run_grid_supplement.py   #   격자 보강
│   └── ...
│
├── legacy/                      # 루트 레거시 Python (solver_gyroid.py 등)
│
├── results/
│   ├── campaign_plan31v/        # plan 3.1V 핵심 산출물 (CSV, PNG)
│   ├── campaign_legacy/         # 이전 캠페인 결과
│   └── l2a_vti/                 # L2A VTR 진단 데이터
│
├── logs/
│   ├── plan31v/                 # 야간 파이프라인 로그
│   ├── legacy/                  # 이전 로그
│   └── analysis/                # 분석·배치 로그
│
├── archive/                     # 검증용 레거시 (Results_EmptyDuct_* 등, 대용량 NPY)
│
├── docs/
│   ├── PROJECT_MASTER_PLAN_FINAL.md  # 통합 수행계획서
│   ├── plans/                   # plan_1.1V ~ plan_3.1V 계획서 원본
│   ├── reports/                 # 결과보고서·분석보고서
│   ├── verification/            # 검증·격자독립성 문서
│   ├── instructions/            # 실행지시서·절차
│   └── theory/                  # 이론·수식 검증
│
├── paper/
│   └── jkcs/                    # JKCS 논문용 LaTeX 프로젝트
│
├── geometry_openscad/           # OpenSCAD 기하 정의
├── geometry_exchange_ansys/     # ANSYS용 기하 교환 (STEP, STL)
└── .venv_v32/                   # Python 가상환경 (git 제외)
```

## 핵심 결과 (plan 3.1V)

| 항목 | 결과 |
|------|------|
| BO 평가 | 100회 (85 OK, 15 FAIL) |
| Pareto 전면 | 50점 |
| Top-5 설계 | A~E 선정 완료 |
| 재현성 CV | ≪ 0.1% |

본 논문 데이터는 `results/campaign_plan31v/`에 보관.

## 사용 방법

```bash
cd taichi_lbm_ref_gyroid
pip install -r requirements.txt
bash run_overnight.sh 2>&1 | tee logs/plan31v/overnight.txt
```

## 환경

- Python 3.13.2, Taichi 1.7.4, arch=cuda
- 가상환경: `.venv_v32`

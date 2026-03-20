# Taichi LBM Ref Gyroid — File Inventory

프로젝트 전체 파일 인벤토리. `geometry_exchange_ansys/` 및 `.venv_v32/` 제외.

---

## Root / Config

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `README.md` | ~4 KB | — | — | 프로젝트 개요 |
| `requirements.txt` | ~1 KB | — | — | Python 의존성 목록 |
| `.gitignore` | ~1 KB | — | — | Git 무시 패턴 |
| `run_overnight.sh` | ~1 KB | — | — | 야간 일괄 실행 셸 스크립트 |

---

## solver/

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `solver/__init__.py` | <1 KB | — | — | 패키지 초기화 |
| `solver/taichi_lbm_core.py` | 23.6 KB | — | — | D3Q19 MRT LBM 코어 솔버 |

---

## scripts/

31개 Python + 2개 Shell 스크립트.

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `scripts/*.py` (31 files) | various | plan31v / legacy | various | BO, 시각화, 진단, 후처리 스크립트 |
| `scripts/*.sh` (2 files) | various | — | — | 실행 보조 셸 스크립트 |

---

## results/campaign_plan31v/

Plan 3.1V 핵심 산출물 — 논문 데이터 소스.

### CSV (10 files)

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `results/campaign_plan31v/bo_results_v2.csv` | 15.5 KB | plan31v | Fig. 2 (BO convergence) | BO 최적화 전체 결과 (100행) |
| `results/campaign_plan31v/pareto_front.csv` | 8.4 KB | plan31v | Fig. 3, Table 3 | Pareto 프론트 해집합 (50행) |
| `results/campaign_plan31v/top5_selected.csv` | 0.9 KB | plan31v | Table 3 | 최종 선정 Top-5 설계 (5행) |
| `results/campaign_plan31v/ghsv_sensitivity.csv` | 2.5 KB | plan31v | Table 4 | GHSV 민감도 분석 결과 (25행) |
| `results/campaign_plan31v/forchheimer.csv` | 2.9 KB | plan31v | Table 5 | Forchheimer 압력강하 데이터 (25행) |
| `results/campaign_plan31v/forchheimer_fit.csv` | 0.6 KB | plan31v | Table 5 | Forchheimer 피팅 계수 (5행) |
| `results/campaign_plan31v/flow_metrics.csv` | 0.6 KB | plan31v | Table 6 | 유동 성능 지표 요약 (5행) |
| `results/campaign_plan31v/repeatability.csv` | 1.0 KB | plan31v | §4.3 | 반복성 검증 원시 데이터 |
| `results/campaign_plan31v/repeatability_summary.csv` | 0.4 KB | plan31v | §4.3 | 반복성 검증 요약 통계 |
| `results/campaign_plan31v/grid_supplement.csv` | 2.9 KB | plan31v | supplementary | 격자 독립성 검증 데이터 (22행) |

### PNG — Main Figures (7 files)

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `results/campaign_plan31v/pareto_plot.png` | 204.4 KB | plan31v | Fig. 3 | Pareto 프론트 시각화 |
| `results/campaign_plan31v/top5_A_vz_xy.png` | 56.8 KB | plan31v | Fig. 4 | Design A — vz XY 단면 |
| `results/campaign_plan31v/top5_B_vz_xy.png` | 64.7 KB | plan31v | Fig. 4 | Design B — vz XY 단면 |
| `results/campaign_plan31v/top5_C_vz_xy.png` | 66.9 KB | plan31v | Fig. 4 | Design C — vz XY 단면 |
| `results/campaign_plan31v/top5_D_vz_xy.png` | 52.9 KB | plan31v | Fig. 4 | Design D — vz XY 단면 |
| `results/campaign_plan31v/top5_E_vz_xy.png` | 66.1 KB | plan31v | Fig. 4 | Design E — vz XY 단면 |
| `results/campaign_plan31v/top5_A_omega_xy.png` | 51.3 KB | plan31v | Fig. 5 | Design A — vorticity XY 단면 |
| `results/campaign_plan31v/top5_B_omega_xy.png` | 62.0 KB | plan31v | Fig. 5 | Design B — vorticity XY 단면 |
| `results/campaign_plan31v/top5_C_omega_xy.png` | 68.8 KB | plan31v | Fig. 5 | Design C — vorticity XY 단면 |
| `results/campaign_plan31v/top5_D_omega_xy.png` | 53.5 KB | plan31v | Fig. 5 | Design D — vorticity XY 단면 |
| `results/campaign_plan31v/top5_E_omega_xy.png` | 57.9 KB | plan31v | Fig. 5 | Design E — vorticity XY 단면 |

### PNG — Supplementary (11 files)

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `results/campaign_plan31v/pareto_params.png` | 38.6 KB | plan31v | supplementary | Pareto 파라미터 분포 |
| `results/campaign_plan31v/top5_A_vtrans_xy.png` | 51.3 KB | plan31v | supplementary | Design A — 횡방향 속도 XY |
| `results/campaign_plan31v/top5_B_vtrans_xy.png` | 49.7 KB | plan31v | supplementary | Design B — 횡방향 속도 XY |
| `results/campaign_plan31v/top5_C_vtrans_xy.png` | 62.7 KB | plan31v | supplementary | Design C — 횡방향 속도 XY |
| `results/campaign_plan31v/top5_D_vtrans_xy.png` | 48.5 KB | plan31v | supplementary | Design D — 횡방향 속도 XY |
| `results/campaign_plan31v/top5_E_vtrans_xy.png` | 54.6 KB | plan31v | supplementary | Design E — 횡방향 속도 XY |
| `results/campaign_plan31v/top5_A_flow.png` | 133.0 KB | plan31v | supplementary | Design A — 유동 종합 |
| `results/campaign_plan31v/top5_B_flow.png` | 154.4 KB | plan31v | supplementary | Design B — 유동 종합 |
| `results/campaign_plan31v/top5_C_flow.png` | 172.9 KB | plan31v | supplementary | Design C — 유동 종합 |
| `results/campaign_plan31v/top5_D_flow.png` | 130.5 KB | plan31v | supplementary | Design D — 유동 종합 |
| `results/campaign_plan31v/top5_E_flow.png` | 156.3 KB | plan31v | supplementary | Design E — 유동 종합 |

---

## results/campaign_legacy/

이전 BO/Top3/Gyroid 진단 결과 (참고용).

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `results/campaign_legacy/` | various | legacy | — | 이전 캠페인 산출물 아카이브 |

---

## results/l2a_vti/

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `results/l2a_vti/` | various | validation | — | Reference 6x6 L2A VTR 진단 (8 time steps) |

---

## legacy/ (Root-level)

루트에서 이동된 레거시 Python 파일 11개.

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `legacy/*.py` (11 files) | various | legacy | — | 루트에서 이동된 이전 버전 스크립트 |

---

## Archive (results/ root-level)

| Path | Size | Campaign | Paper Mapping | Description |
|------|------|----------|---------------|-------------|
| `Results_*/ (5 dirs)` | various | legacy | — | 이전 실행 결과 디렉토리 |
| `*.npy (3 files)` | various | legacy | — | NumPy 배열 캐시 |
| `*.png (2 files)` | various | legacy | — | 이전 시각화 PNG |

---

## docs/

76개 마크다운 문서.

| Subdirectory | File Count | Campaign | Description |
|-------------|------------|----------|-------------|
| `docs/plans/` | 18 | — | 버전별 실행 계획서 |
| `docs/reports/` | 38 | — | 실행 결과 보고서 |
| `docs/verification/` | 12 | validation | 검증 문서 |
| `docs/instructions/` | 9 | — | 작업 지침서 |
| `docs/theory/` | 3 | — | 이론 배경 문서 |

---

## Logs

| Subdirectory | File Count | Campaign | Description |
|-------------|------------|----------|-------------|
| `logs/plan31v/` | 8 | plan31v | Plan 3.1V 실행 로그 |
| `logs/legacy/` | 11 | legacy | 이전 실행 로그 |
| `logs/analysis/` | 23+ | — | 분석 로그 |

---

*Generated: 2026-03-20*

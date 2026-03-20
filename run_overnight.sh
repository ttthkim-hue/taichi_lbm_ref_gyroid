#!/bin/bash
# run_overnight.sh — plan_3.1V 야간 10시간 자동 실행
set -eo pipefail
cd /mnt/h/taichi_lbm_ref_gyroid
source .venv_v32/bin/activate
export PYTHONUNBUFFERED=1

mkdir -p logs/plan31v results/campaign_plan31v

echo "=========================================="
echo "plan_3.1V overnight run started: $(date)"
echo "=========================================="

echo ""
echo "=== Phase 1: BO 재실행 (100회, a∈[3,12]) ==="
python scripts/run_bo_pipeline.py \
    --n_init 20 --n_iter 80 \
    --a_min 3.0 --a_max 12.0 \
    --output results/campaign_plan31v/bo_results_v2.csv \
    2>&1 | tee logs/plan31v/phase1_bo.txt

echo ""
echo "=== Phase 1b: Pareto 분석 (Top-5) ==="
python scripts/analyze_pareto.py \
    --input results/campaign_plan31v/bo_results_v2.csv \
    --top 5 \
    2>&1 | tee logs/plan31v/phase1b_pareto.txt

echo ""
echo "=== Phase 2: 다중 GHSV 압력손실 ==="
python scripts/run_ghsv_sensitivity.py \
    --top5 results/campaign_plan31v/top5_selected.csv \
    --output results/campaign_plan31v/ghsv_sensitivity.csv \
    2>&1 | tee logs/plan31v/phase2_ghsv.txt

echo ""
echo "=== Phase 3: Forchheimer 비선형 ==="
python scripts/run_forchheimer.py \
    --top5 results/campaign_plan31v/top5_selected.csv \
    --output results/campaign_plan31v/forchheimer.csv \
    --output-fit results/campaign_plan31v/forchheimer_fit.csv \
    2>&1 | tee logs/plan31v/phase3_forch.txt

echo ""
echo "=== Phase 4: 유동 특성화 + VTI ==="
python scripts/run_flow_metrics.py \
    --top5 results/campaign_plan31v/top5_selected.csv \
    --output results/campaign_plan31v/flow_metrics.csv \
    2>&1 | tee logs/plan31v/phase4_flow.txt

echo ""
echo "=== Phase 5: 반복 재현성 ==="
python scripts/run_repeatability.py \
    --output results/campaign_plan31v/repeatability.csv \
    --output-summary results/campaign_plan31v/repeatability_summary.csv \
    2>&1 | tee logs/plan31v/phase5_repeat.txt

echo ""
echo "=== Phase 6: 설계 공간 경계 보강 ==="
python scripts/run_grid_supplement.py \
    --bo-csv results/campaign_plan31v/bo_results_v2.csv \
    --output results/campaign_plan31v/grid_supplement.csv \
    2>&1 | tee logs/plan31v/phase6_grid.txt

echo ""
echo "=========================================="
echo "전체 완료: $(date)"
echo "=========================================="
echo "결과 파일:"
ls -lh results/campaign_plan31v/*.csv results/campaign_plan31v/*.png 2>/dev/null || true

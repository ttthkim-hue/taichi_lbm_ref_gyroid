#!/bin/bash
# plan_2.2V 수정 후 검증: L2-B → L2-A → Gyroid 3-g 순차 실행
# 사용법: nohup bash scripts/run_plan22v_verify.sh > plan22v_verify.log 2>&1 &

set -e
cd "$(dirname "$0")/.."
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_DIR="logs/plan22v_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo "=== plan_2.2V 검증 시작: $(date) ===" | tee "$LOG_DIR/00_summary.txt"

echo "[1/3] L2-B 주기BC 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_l2_periodic_plan19v.py 2>&1 | tee "$LOG_DIR/01_L2B_periodic.txt"
echo "[1/3] L2-B 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

echo "[2/3] L2-A 저유속 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_l2_ref6x6_plan17v.py 2>&1 | tee "$LOG_DIR/02_L2A_low_velocity.txt"
echo "[2/3] L2-A 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

echo "[3/3] Gyroid 3-g 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_gyroid_3ghsv_plan191v.py 2>&1 | tee "$LOG_DIR/03_gyroid_3ghsv.txt"
echo "[3/3] Gyroid 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

echo "=== plan_2.2V 검증 완료: $(date) ===" | tee -a "$LOG_DIR/00_summary.txt"
echo "로그: $LOG_DIR"
grep -h "\[결과\] K_sim" "$LOG_DIR"/*.txt 2>/dev/null || true
echo "K(A) vs K(B) 비교는 위 [결과] K_sim(A), K_sim(B) 값으로 수행."

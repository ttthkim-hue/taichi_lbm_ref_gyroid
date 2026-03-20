#!/bin/bash
# plan_2.1V (plan_1.92V) 자동 배치 — 6시간 무인 실행
# 사용법: nohup bash scripts/run_batch_plan21v.sh > batch_log.txt 2>&1 &
# set -e: 에러 시 중단. 개별 Python 스크립트는 try-except 후 traceback 출력 권장.

set -e
cd "$(dirname "$0")/.."
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_DIR="logs/batch_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo "=== plan_2.1V 배치 시작: $(date) ===" | tee "$LOG_DIR/00_summary.txt"

# ── Step 1: L2-A 저유속 131격자 수렴 (~70분) ──
echo "[Step 1/5] L2-A 저유속 131격자 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_l2_ref6x6_plan17v.py 2>&1 | tee "$LOG_DIR/01_L2A_low_velocity.txt"
echo "[Step 1/5] 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

# ── Step 2: L2-B 주기BC 131격자 (~70분) ──
echo "[Step 2/5] L2-B 주기BC 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_l2_periodic_plan19v.py 2>&1 | tee "$LOG_DIR/02_L2B_periodic.txt"
echo "[Step 2/5] 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

# ── Step 3: L1 빠른 재확인 5000스텝 (~30분) ──
echo "[Step 3/5] L1 빠른 재확인 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_l1_quick_plan19v.py 2>&1 | tee "$LOG_DIR/03_L1_quick.txt"
echo "[Step 3/5] 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

# ── Step 4: Gyroid 3-GHSV 스케일링 (~210분) ──
echo "[Step 4/5] Gyroid 3-GHSV 시작: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/run_gyroid_3ghsv_plan191v.py 2>&1 | tee "$LOG_DIR/04_gyroid_3ghsv.txt"
echo "[Step 4/5] 완료: $(date)" | tee -a "$LOG_DIR/00_summary.txt"

# ── Step 5: 결과 요약 자동 생성 ──
echo "[Step 5/5] 결과 요약 생성: $(date)" | tee -a "$LOG_DIR/00_summary.txt"
python scripts/summarize_batch_plan21v.py "$LOG_DIR" 2>&1 | tee "$LOG_DIR/05_final_summary.txt"

echo "=== plan_2.1V 배치 완료: $(date) ===" | tee -a "$LOG_DIR/00_summary.txt"

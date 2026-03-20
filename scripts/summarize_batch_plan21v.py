#!/usr/bin/env python3
"""
plan_2.1V (plan_1.92V) 배치 완료 후 로그에서 핵심 수치를 추출하여 한 페이지 요약 생성.
사용: python scripts/summarize_batch_plan21v.py <LOG_DIR>
"""
import sys
import os

log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs/batch_latest"
if not os.path.isdir(log_dir):
    print(f"오류: 디렉터리가 없습니다: {log_dir}")
    sys.exit(1)

print("=" * 60)
print("plan_2.1V 배치 결과 요약")
print("=" * 60)

files = sorted(f for f in os.listdir(log_dir) if f.endswith(".txt") and f != "00_summary.txt")
keywords = ["판정", "오차", "PASS", "FAIL", "K_sim", "ΔP", "delta_P", "u_mean", "CV", "결과", "K 평균", "편차"]

for fname in files:
    path = os.path.join(log_dir, fname)
    if not os.path.isfile(path):
        continue
    print(f"\n--- {fname} ---")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  (읽기 실패: {e})")
        continue
    # plan §2: 마지막 30줄에서 핵심 추출
    tail = lines[-30:] if len(lines) > 30 else lines
    for line in tail:
        if any(kw in line for kw in keywords):
            print(line.rstrip())

print("\n" + "=" * 60)
print("귀환 후 위 판정을 확인하고 plan_2.1V 체크리스트 갱신")

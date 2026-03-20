# 작업지시서 — plan_2.1V (6시간 자동 배치 실행)

**작성일:** 2026-03-18  
**상황:** 6시간 자리 비움. GPU 자동 실행 후 귀환 시 결과 확인.

---

## 0. 현재 상태 진단

| 항목 | 상태 | 비고 |
|------|------|------|
| dt τ기반 고정 | ✅ 완료 | p_scale=7.68 고정 확인 |
| L1 빈 덕트 | ✅ PASS | 오차 7.5% |
| L2 131 저유속 (dt고정) | 🔄 1k스텝만 확인 | Δρ=0.37%, 수렴 필요 |
| 주기BC + Guo forcing | ✅ 구현됨 | 미검증 |
| Gyroid ε, S_v | ✅ 실측 | ε=0.806, S_v=2537 |
| Gyroid 3-GHSV | ❌ 미실행 | 스크립트 준비됨 |

---

## 1. 마스터 스크립트 작성

아래 내용으로 `scripts/run_batch_plan21v.sh` 를 생성하고 실행한다.

```bash
#!/bin/bash
# plan_2.1V 자동 배치 — 6시간 무인 실행
# 사용법: nohup bash scripts/run_batch_plan21v.sh > batch_log.txt 2>&1 &

set -e  # 에러 시 중단 (개별 스크립트 내 try-except로 처리 권장)
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
```

---

## 2. 결과 요약 스크립트

`scripts/summarize_batch_plan21v.py` — 각 로그에서 핵심 판정을 추출하여 한 페이지 요약 생성.

```python
"""
배치 완료 후 로그에서 핵심 수치를 grep하여 요약 출력.
각 스크립트가 마지막에 [판정] 또는 [결과] 태그로 핵심을 출력한다고 가정.
"""
import sys, os, re

log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs/batch_latest"

print("=" * 60)
print("plan_2.1V 배치 결과 요약")
print("=" * 60)

files = sorted(f for f in os.listdir(log_dir) if f.endswith('.txt') and f != '00_summary.txt')
for fname in files:
    path = os.path.join(log_dir, fname)
    print(f"\n--- {fname} ---")
    with open(path) as f:
        lines = f.readlines()
    # 마지막 30줄에서 핵심 추출
    tail = lines[-30:] if len(lines) > 30 else lines
    for line in tail:
        if any(kw in line for kw in ['판정', '오차', 'PASS', 'FAIL', 'K_sim', 'ΔP', 'delta_P', 'u_mean', 'CV']):
            print(line.rstrip())

print("\n" + "=" * 60)
print("귀환 후 위 판정을 확인하고 plan_2.1V 체크리스트 갱신")
```

---

## 3. 각 스크립트 확인 사항

실행 전 에이전트가 확인할 것 (스크립트가 이미 존재한다면 수정 사항만):

### 3.1 Step 1: `run_l2_ref6x6_plan17v.py`

| 확인 항목 | 올바른 값 |
|-----------|-----------|
| dt 결정 | τ 기반 고정 (dt = ν_lb × dx² / ν_phys = **3.6e-5**) |
| NX, NY | **131** |
| u_in | Δρ < 3% 되도록 설정 (u_in ≈ **0.0123** m/s) |
| p_scale | **7.68** (u_in에 무관하게 고정) |
| 수렴 기준 | ΔP 변화율 3회 연속 < 0.1%, max 100k |
| 출력 | ΔP_sim, ΔP_theory, 오차, CV, K_sim(A), Δρ, 판정 |

**K_sim(A) 산출이 포함되어 있는지 확인:**

```python
K_sim_A = u_in * mu * L_measure / dp_sim  # Darcy 투과율
print(f"[결과] K_sim(A) = {K_sim_A:.4e} m²")
```

### 3.2 Step 2: `run_l2_periodic_plan19v.py`

| 확인 항목 | 올바른 값 |
|-----------|-----------|
| mode | `periodic_body_force` |
| NX, NY | **131** |
| ΔP_target | **3.819 Pa** (이론 HP) |
| g_lbm | set_body_force(ΔP=3.819, L=0.107) |
| 검증 지표 | 정상상태 u_mean_z (유체 평균 vz) |
| PASS | u_mean vs u_channel_theory(**0.449**) 오차 < 5% |
| 출력 | u_mean, u_theory, 오차, K_sim(B), 판정 |

**K_sim(B) 산출:**

```python
u_superficial = u_mean_fluid * epsilon  # 또는 전체 단면 평균
K_sim_B = u_superficial * mu * L_measure / dp_target
print(f"[결과] K_sim(B) = {K_sim_B:.4e} m²")
```

> ⚠️ u_superficial 정의: 유체+고체 전체 단면 기준 평균 유속. u_mean_fluid × ε로 산출.

### 3.3 Step 3: `run_l1_quick_plan19v.py`

| 확인 항목 | 올바른 값 |
|-----------|-----------|
| dt | τ 기반 고정 (기존 L1과 동일 3.6e-5) |
| 스텝 | **5000** (수렴 확인용, early stop 불필요) |
| 출력 | ΔP at 5000 step (≈0.07이면 기존과 일치) |

### 3.4 Step 4: `run_gyroid_3ghsv_plan191v.py`

| 확인 항목 | 올바른 값 |
|-----------|-----------|
| 형상 | Gyroid a=5mm, t=0.3, 131×131×550 |
| mode | `periodic_body_force` |
| 3 GHSV | 아래 표 참조 |

| GHSV | u_target (m/s) | ΔP_guess (Pa) | 비고 |
|------|----------------|---------------|------|
| 2,000 | 0.0556 | 0.5~2 (추정) | 초기 추정으로 g 설정 |
| 5,000 | 0.1389 | 3~10 (추정) | |
| 10,000 | 0.2778 | 10~40 (추정) | |

> ⚠️ Gyroid의 ΔP를 사전에 모르므로, 주기BC에서는 **g를 먼저 설정하고 u_mean을 측정**하는 방식이 맞다. 즉:
> 1. 목표 u_target으로부터 Kozeny-Carman으로 ΔP 초기 추정
> 2. g_lbm = ΔP_guess / (ρ_phys × L) × dt²/dx
> 3. 시뮬 실행 후 u_mean 측정
> 4. K = u_mean × μ × L / ΔP (ΔP = g_phys × ρ × L)
>
> **또는 더 간단하게:** g를 임의로 3개 다른 값으로 주고, 각각에서 u_mean과 K를 산출. K가 일정하면 Darcy 영역 확인.

**추천 방식 (g 직접 지정):**

```python
g_values = [1e-6, 5e-6, 2e-5]  # 격자 단위
# 각 g에서:
#   시뮬 → u_mean 측정
#   ΔP = ρ_phys × (g × dx/dt²) × L
#   K = u_mean × μ × L / ΔP
# K 3개가 ±10% 이내면 PASS
```

이 방식이 GHSV를 몰라도 되고, 순수하게 투과율 일정성만 검증하므로 깔끔하다.

**출력:**

```
[Gyroid K 스케일링]
  g=1e-6: u_mean={}, ΔP={} Pa, K={:.4e} m²
  g=5e-6: u_mean={}, ΔP={} Pa, K={:.4e} m²
  g=2e-5: u_mean={}, ΔP={} Pa, K={:.4e} m²
  K 편차: {}%
  판정: PASS/FAIL (기준: 편차 < 10%)
```

---

## 4. 실행 방법

```bash
# 스크립트에 실행 권한 부여
chmod +x scripts/run_batch_plan21v.sh

# nohup으로 백그라운드 실행
nohup bash scripts/run_batch_plan21v.sh > batch_log.txt 2>&1 &

# 프로세스 확인
jobs -l
# 또는
ps aux | grep run_batch
```

**예상 소요:**

| Step | 내용 | 예상 시간 |
|------|------|-----------|
| 1 | L2-A 저유속 131 | ~70분 |
| 2 | L2-B 주기BC 131 | ~70분 |
| 3 | L1 빠른 재확인 | ~30분 |
| 4 | Gyroid 3-g 스케일링 | ~210분 (70분 × 3) |
| 5 | 요약 생성 | ~1분 |
| **합계** | | **~6시간 20분** |

---

## 5. 귀환 후 확인 절차

### 5.1 즉시 확인

```bash
cat logs/batch_*/05_final_summary.txt
```

이 파일에 모든 판정이 요약되어 있다.

### 5.2 판정 기준

| 검증 | PASS 기준 | FAIL 시 조치 |
|------|-----------|-------------|
| L2-A | ΔP 오차 < 5%, CV < 5%, Δρ < 3% | 이론값 재검산, 마스크 확인 |
| L2-B | u_mean 오차 < 5% | Guo forcing 구현 확인, g_lbm 재계산 |
| L2-C | K(A) vs K(B) < 10% | 위 두 개 중 FAIL인 쪽 수정 |
| L1 재확인 | ΔP ≈ 0.07 Pa | dt 변경이 기존 깨뜨림 → 롤백 |
| Gyroid K | 3-g 편차 < 10% | Re 효과(Forchheimer) 가능, g 범위 축소 |

### 5.3 전부 PASS 시 다음 단계

```
→ 격자 독립성 GCI (3-level, ~4시간)
→ Gyroid t 범위 검증 (a, t) → ε 매핑
→ BO 파이프라인 구축
```

---

## 6. 에이전트 실행 전 최종 체크리스트

| # | 확인 사항 | ☐ |
|---|----------|---|
| 1 | `run_l2_ref6x6_plan17v.py`에 dt=τ기반 고정, K_sim(A) 출력 포함 | ☐ |
| 2 | `run_l2_periodic_plan19v.py`에 NX=NY=131, K_sim(B) 출력 포함 | ☐ |
| 3 | `run_l1_quick_plan19v.py`에 dt=τ기반 고정, 5000스텝 | ☐ |
| 4 | `run_gyroid_3ghsv_plan191v.py`에 g 3개, K 산출, 편차 판정 | ☐ |
| 5 | `summarize_batch_plan21v.py` 생성 | ☐ |
| 6 | `run_batch_plan21v.sh` 생성, 실행 권한 | ☐ |
| 7 | 모든 스크립트가 에러 시 traceback 출력 (try-except) | ☐ |
| 8 | GPU 메모리 충분 확인 (131³×550 ≈ 9.4M nodes → ~2.4GB) | ☐ |
| 9 | `nohup` 실행 후 `batch_log.txt` 초기 출력 확인 | ☐ |
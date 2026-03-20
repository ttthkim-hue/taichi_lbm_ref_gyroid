# plan_1.3V §7 / plan_1.4V §4: 격자 독립성 스터디 (3-Level)

**전제:** plan_1.4V §1 빈 덕트 L1 PASS 후 수행.

## 격자 레벨 (plan_1.4V §4)

| Level   | dx     | 격자 크기     | 예상 시간 |
|---------|--------|---------------|-----------|
| Coarse  | 0.4 mm | 64×64×275     | ~8 min    |
| Medium  | 0.2 mm | 127×127×550   | ~70 min   |
| Fine    | 0.15 mm| 169×169×733   | ~180 min  |

총 약 4.3시간. Gyroid **a=5 mm, t=0.3** 고정.

## 절차

- 세 격자에서 수렴까지 실행 후 ΔP (및 S_v) 수집.
- Richardson extrapolation → GCI 산출.
- **PASS 기준: GCI_fine < 5%**

## 실행

- **스크립트:** `scripts/run_gci_3level_plan14v.py`
- 레벨별로 subprocess 실행( Taichi 프로세스당 1회 초기화 대응 ) 후 결과 파일로 ΔP 수집, GCI_fine 계산.
- ΔP, S_v 비교는 동일 스크립트에서 ΔP 기준 GCI만 산출; S_v는 후처리에서 추가 가능.

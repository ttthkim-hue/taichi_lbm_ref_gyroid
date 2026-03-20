# plan_1.5V 완수 요약

**기준:** `docs/plan_1.5V.md`  
**원칙:** 솔버 미수정, 검증 스크립트만 수정/신규.

---

## §1 L1 빈 덕트 — 이론값 발달유동 상관식

- **수정 파일:** `scripts/run_l1_empty_duct_plan13v.py`
- **변경:** 이론 ΔP를 Hagen-Poiseuille 대신 **Shah & London 발달유동 상관식**으로 교체.
  - `L_measure = (z_out - z_in) × dx` (측정면 간 거리)
  - `L⁺ = L_measure / (Dh × Re)`
  - `f_app·Re = 3.44/√(L⁺) + (56.91 + 1.25/(4·L⁺) - 3.44/√(L⁺)) / (1 + 0.00021/(L⁺)²)`
  - `ΔP_theory = (f_app·Re/Re) × (L_measure/Dh) × 0.5 × ρ × u_in²`
- 기존 HP 이론은 주석 처리·비교 참고용 유지.
- **출력:** §1.4 형식 (`[L1 검증 — 발달유동 상관식]`, Dh, Re, L_measure, L⁺, f_app·Re, ΔP_theory, ΔP_sim, 오차, 판정).
- **PASS:** ΔP 오차 < 5%, Q 차이 < 1%, 질량 드리프트 < 0.1%, clips = 0 (4항목 모두).

---

## §2 L2 Reference 6×6

- **신규 파일:** `scripts/run_l2_ref6x6.py`
- **마스크:** `make_ref6x6_voxel()` — 외벽 5 voxel, 내부 격벽 5 voxel(1 mm), 6×6 채널. 단면 유체/전체 = 8464/13689 ≈ **0.618** (검증 통과).
- **이론:** Dh = 3.067 mm, u_channel = 0.449 m/s, Re = 39.1, Le = 6 mm, HP ΔP_theory.
- **실행:** 127×127×550, run_with_logging 수렴까지.
- **CV:** 36채널 개별 유량(ρ·vz 슬라이스) vs Q_total/36, 편차 ±10% 이내.
- **출력:** §2.6 형식. **PASS:** ΔP < 5%, Q < 1%, clips = 0, CV < 10%.

---

## §3 S_v 편차 정량화

- L2 스크립트 종료 전 **S_v 이론값** vs **voxel 유체-고체 경계면 기반 S_v** 산출 후 편차(%) 출력.
- PASS/FAIL 아님. Gyroid S_v 보정용 편차 기록.

---

## 사용자 실행

- **L1 최종 판정:** `python scripts/run_l1_empty_duct_plan13v.py` (수렴까지).
- **L2 최종 판정:** `python scripts/run_l2_ref6x6.py` (수렴까지, S_v·CV 포함).

L1·L2 모두 PASS 시 → plan_1.4V §3 (Gyroid t 범위 검증) 진행.

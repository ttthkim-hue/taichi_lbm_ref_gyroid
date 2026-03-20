# plan_v1.6.V §2.1 L2 스크립트 점검

**대상:** `scripts/run_l2_ref6x6.py`

---

## 3항목 확인

| 항목 | 올바른 값 | 확인 결과 |
|------|-----------|-----------|
| Inlet BC 유속 | u_in = **0.2778 m/s** (덕트 표면유속) | ✅ `TaichiLBMWrapper(..., u_in_phys=u_in)` |
| 이론 ΔP의 유속 | u_channel = **0.449 m/s** | ✅ `u_channel = u_in * (area_duct_mm2 / area_channel_mm2)` |
| 이론 ΔP의 길이 | L_measure = **(z_out - z_in) × dx** | ✅ `L_measure = (z_out - z_in) * DX` |

---

## §2.2 Fanning 이론 반영

- **변경:** `f_Re = 56.91` (Darcy) → **f_Fanning_Re = 14.227**, **ΔP = 4 × f_Fanning × (L_measure/Dh) × 0.5×ρ×u_channel²**
- CV 산출 단면: **(z_out - z_in)/2** → **z_out** (출구 단면, plan §2.5)
- S_v: plan_v1.6.V §2.6 명시, Gyroid 보정용 기록

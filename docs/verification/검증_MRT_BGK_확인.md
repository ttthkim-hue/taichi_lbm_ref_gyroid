# V-MRT 검증: MRT S-matrix 구현 여부 확인 (BGK 대비)

**기준:** `docs/[mainplan]_V1.1.md` §5.1, §9 (R1)  
**대상 코드:** `251224_coding/.../260107_Taichi_LBM/taichi_lbm_solver_v3.py`  
**검증 일자:** 2026-03-17

---

## 1. 결론

| 항목 | 계획서 | 실제 구현 | 검증 |
|------|--------|-----------|------|
| Collision | D3Q19 **MRT-LBM** (τ=0.595 허용) | **D3Q19 BGK** (단일 τ) | ⚠️ **불일치** |

- 코드 내 **MRT S-matrix 미구현.** 솔버는 **BGK(SRT)** collision 사용.
- 근거: docstring 12행 "D3Q19 BGK"; 244~276행 `collide_KBC`에서 `f_star = f - omega*(f - feq)` (단일 relaxation).

---

## 2. 계획서 대조 검증

- §5.1: "코드 내 MRT S-matrix 구현 여부 **반드시 확인**" → **확인 완료.** 결과: BGK로 동작.
- §9 R1: "MRT가 실제로 BGK로 동작 → S-matrix 확인, MRT vs BGK 테스트" → **확인 반영.**

---

## 3. 권장 조치

- MRT 전환: Lallemand & Luo (2000) D3Q19 MRT M·S 도입.  
- 또는 BGK 유지 시 τ 안정 범위 재검토 후 L1 재검증.

**V-MRT 검증 결과:** 지시사항(확인) 완수. 구현은 BGK로 판정됨. 계획서 §5.1·§9 R1 반영 확인.

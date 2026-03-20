# V-geo 검증: 3종 형상 STL 및 파이프라인

**기준:** `docs/[mainplan]_V1.1.md` §1.2, §6, §7  
**검증 일자:** 2026-03-17

---

## 1. 3종 형상 STL 존재 확인

| 형상 | 파일 경로 | 존재 |
|------|-----------|------|
| 빈 덕트 | `geometry_openscad/empty_duct_v32.stl` | ✅ |
| Reference 6×6 | `geometry_openscad/reference_6x6_v32.stl` | ✅ |
| Gyroid | `geometry_openscad/gyroid_taichi_formula.stl`, `geometry_openscad/gyroid_duct_v32_final.stl` | ✅ |

계획서: "3종 형상 STL(빈 덕트, Reference 6×6, Gyroid)은 확인용으로 확정" → **검증 통과.**

---

## 2. 파이프라인 문구 대조

- **§1.2:** STL→Voxel 미채택. Taichi 커널 → NumPy 추출 → OpenSCAD STL(최종 검증).  
- **§6:** 형상은 Taichi 커널 또는 .npy 마스크 주입; NumPy 추출 → OpenSCAD STL 최종검증.

현재 프로젝트: `geometry_openscad/`, 아카이브 `taichi_lbm_solver_v3.py` 등 존재. 통합 시 §6 구조로 정리 예정.  
**검증:** 계획서와 정합.

---

**V-geo 검증 결과:** 누락 없음. 3종 STL 확인용 확정 및 Taichi 커널→NumPy→OpenSCAD STL 파이프라인 반영 확인됨.

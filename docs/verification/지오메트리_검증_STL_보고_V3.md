# 지오메트리 검증 STL 보고 (V3.1 기준 최신)

현재 도메인 기준으로 **빈 덕트**, **Reference 6×6**, **Gyroid** STL을 생성해 검증용으로 보고합니다.

---

## 1. 빈 덕트 (Empty Duct)

| 항목 | 값 |
|------|-----|
| LBM 격자 | 127×127×520 셀 (V3.1 통일) |
| dx | 0.2 mm |
| 물리 치수 | **25.4 × 25.4 × 104 mm** (1 inch 단면, 전부 유체) |
| 마스크 | `verify_duct_25.4mm_mask.npy` |

**STL**
- 소스: `geometry_openscad/empty_duct.scad`
- 출력: `geometry_openscad/empty_duct.stl`
- 중공 덕트(벽 0.5 mm), 내부 25.4×25.4×104 mm가 비어 보이도록 표현.

---

## 2. 자이로이드 (Gyroid)

| 항목 | 값 |
|------|-----|
| 도메인 | **25.4×25.4×110 mm** (구조체 길이, 버퍼 제외) |
| 외벽 | 1 mm (x,y 경계 0~1 mm, 24.4~25.4 mm) |
| 내부 gyroid | **23.4×23.4×110 mm** 에만 TPMS (V3.1 방법 A) |
| 수식 | t_level=0.768+0.35×t, 동일 F 공식 |

**STL**
- 스크립트: `geometry_openscad/gyroid_to_stl.py`
- 출력: `geometry_openscad/gyroid.stl`
- 명령: `python3 gyroid_to_stl.py --a 5 --t 0 --res 50 --out gyroid.stl`
- 외벽 1 mm + 내부 23.4 mm 영역만 gyroid로 일치.

---

## 3. Reference 6×6

| 항목 | 값 |
|------|-----|
| 치수 | **25.4×25.4×100 mm** (1 inch), 외벽 1 mm, 내벽 1 mm, 채널 3.067 mm, 36채널 |
| STL | `geometry_openscad/reference_6x6.stl` |

---

## 4. 파일 위치 요약

| 형상 | 소스 | STL |
|------|------|-----|
| 빈 덕트 | `empty_duct.scad` | `empty_duct.stl` |
| Gyroid | `gyroid_to_stl.py` | `gyroid.stl` |
| Reference 6×6 | `reference_6x6.scad` | `reference_6x6.stl` |

모두 **V3.1 현재 기준**으로 재생성되어 있으며, 메시 뷰어로 치수·형상 검증 가능합니다.

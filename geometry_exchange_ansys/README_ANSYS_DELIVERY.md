# ANSYS 전달 패키지 (STEP 형상)

다른 기관에서 ANSYS로 해석할 수 있도록 STEP(AP214) 형상 파일과 수식/파라미터 문서를 제공합니다.

---

## 1. 포함 파일

| 파일 | 설명 |
|------|------|
| empty_duct_v32.step | 빈 덕트 (외부 25.4×25.4×110 mm, 벽 1 mm) |
| reference_6x6_v32.step | 레퍼런스 6×6 채널 (버퍼 + 메인 100 mm) |
| gyroid_network_a5_t03.step | Network 자이로이드 (a=5 mm, t=0.3) + 외벽 |
| generate_gyroid_step.py | 파라미터(a, t, res 등)로 자이로이드 STEP 재생성 스크립트 |
| GEOMETRY_FORMULAS_AND_PARAMS.md | 수식, 치수, 파라미터, LBM 대응 설명 |
| README_ANSYS_DELIVERY.md | 본 가이드 |

---

## 2. ANSYS SpaceClaim에서 불러오기

1. **File → Open** 또는 해당 메뉴에서 STEP 파일 선택
2. **Import** 옵션:
   - STEP 파일이 Faceted(삼각 메쉬 기반)일 수 있음 → **Facets → B-Surface** 변환 옵션 사용 권장
   - 해석용으로는 **Body** 수, **Bounding box** 확인 후 사용

---

## 3. Faceted STEP 처리

- 자이로이드 STEP은 marching cubes 메쉬를 Solid로 변환한 것이므로, 일부 CAD에서 **Faceted** 로 인식될 수 있음
- ANSYS/SpaceClaim에서:
  - **Facets → B-Surface** (또는 유사 옵션)으로 보다 매끄러운 면으로 변환 가능
  - 해상도가 낮으면 각진 면이 보일 수 있음 → `generate_gyroid_step.py --res 60` 등으로 재생성 시 더 촘촘한 메쉬

---

## 4. 해상도별 용량/품질 가이드 (generate_gyroid_step.py)

| --res | 용량/품질 | 비고 |
|-------|-----------|------|
| 30 | 작은 파일, 빠른 변환 | 검증/테스트용 |
| 60 | 중간 (기본값) | 권장, 변환 시간 수 분 소요 가능 |
| 120 | 큰 파일, 고해상도 | 고품질 형상 필요 시 |

---

## 5. 전달 전 검증 체크리스트

- [ ] **Body 수**: 각 STEP에서 기대하는 Body 개수(예: 1)와 일치하는지
- [ ] **Bounding box**: 25.4 × 25.4 × 110 mm (또는 동일 치수) 범위인지
- [ ] **Import 경고**: ANSYS/SpaceClaim import 시 경고 메시지 확인 후 필요 시 Facets → B-Surface 등 적용
- [ ] **단위**: mm 기준 (ANSYS 단위 설정과 일치시키기)

---

## 6. 자이로이드 STEP 재생성 예시

```bash
# 기본 (a=5, t=0.3, 외벽 포함)
python generate_gyroid_step.py

# 해상도 80, 출력 파일 지정
python generate_gyroid_step.py --a 5 --t 0.3 --res 80 --out my_gyroid.step

# 외벽 없이 자이로이드만
python generate_gyroid_step.py --no-duct --out gyroid_only.step

# STEP 생성 시 동일 메쉬를 STL로도 저장 (시각 검증용)
python generate_gyroid_step.py --stl gyroid_network_a5_t03_vis.stl

# FreeCAD 없이 STL만 생성 (메쉬뷰어로 빠른 확인)
python generate_gyroid_step.py --stl-only --stl gyroid_network_a5_t03_vis.stl
```

### 6.2 3종 형상 STL 일괄 생성 (시각 검증용, FreeCAD 불필요)

```bash
# 3종 모두 (빈 덕트, 6×6 채널, 자이로이드+외벽)
python generate_all_stl.py

# 고해상도
python generate_all_stl.py --res 0.3
```

> `generate_all_stl.py`는 Taichi LBM과 동일한 voxel 기반 방식으로 **외벽 1mm가 포함된** STL을 생성합니다.

수식 및 파라미터 상세는 **GEOMETRY_FORMULAS_AND_PARAMS.md** 를 참고하세요.

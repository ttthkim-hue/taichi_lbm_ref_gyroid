# geometry_exchange_ansys 프로젝트 종합분석보고서

**대상 디렉터리:** `geometry_exchange_ansys/`  
**작성일:** 2026-03-19  
**목적:** ANSYS 등 외부 CAD/CFD 툴 전달용 STEP 형상 생성 파이프라인의 구조, 역할, 사용법 및 검증 방법을 상세·정확히 정리.

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| **목적** | 다른 기관에서 ANSYS로 해석할 수 있도록 **STEP(AP214) 형상 파일**과 수식/파라미터 문서를 제공하는 패키지 구축 |
| **도메인** | 외부 25.4×25.4×110 mm, 벽 1 mm, 내부 유로 23.4×23.4 mm, 버퍼 0~5 / 105~110 mm, 메인 5~105 mm |
| **형상 종류** | (1) 빈 덕트, (2) 레퍼런스 6×6 채널, (3) 파라미터화 자이로이드 네트워크 |
| **의존성** | Python 3, NumPy, scikit-image 또는 SciPy, **FreeCAD** (freecadcmd) |

---

## 2. 디렉터리 구조 및 파일 역할

### 2.1 파일 목록

| 파일 | 유형 | 역할 |
|------|------|------|
| `generate_gyroid_step.py` | Python | **핵심 파이프라인**: 자이로이드 φ 수식 → marching cubes → 임시 STL → FreeCAD로 STEP 변환 및 선택적 덕트 융합 |
| `stl_to_step_freecad.py` | FreeCAD 스크립트 | STL → Solid(B-Rep) → STEP 내보내기; 선택적으로 `empty_duct_v32.step`과 fuse |
| `export_empty_duct_step.py` | FreeCAD 스크립트 | B-Rep 빈 덕트(25.4×25.4×110, 벽 1 mm) 생성 후 STEP 내보내기 |
| `export_reference_6x6_step.py` | FreeCAD 스크립트 | B-Rep 레퍼런스 6×6 채널(36채널 + 입출구 버퍼) 생성 후 STEP 내보내기 |
| `verify_bbox.py` | Python | 전달용 STEP 3종 존재 여부 및 명목 bbox(25.4×25.4×110 mm) 검증 스크립트 |
| `GEOMETRY_FORMULAS_AND_PARAMS.md` | 문서 | 수식, 치수, 파라미터, LBM 대응 관계 정리 |
| `README_ANSYS_DELIVERY.md` | 문서 | ANSYS 전달 가이드(불러오기, Faceted 처리, 해상도 가이드, 재생성 예시) |
| `empty_duct_v32.step` | STEP | 빈 덕트 고정 형상 (스크립트로 재생성 가능) |
| `reference_6x6_v32.step` | STEP | 레퍼런스 6×6 채널 고정 형상 |
| `gyroid_network_a5_t03.step` | STEP | 자이로이드 a=5 mm, t=0.3 + 외벽 (파이프라인 기본 출력) |
| `gyroid_network_a5_t03_noduct.step` | STEP | 동일 자이로이드, 덕트 없음 (--no-duct) |
| `gyroid_network_a5_t03_with_duct.step` | STEP | 동일 자이로이드 + 덕트 (--with-duct, 기본) |

### 2.2 생성·의존 관계

```
export_empty_duct_step.py (FreeCAD)  →  empty_duct_v32.step
export_reference_6x6_step.py (FreeCAD) →  reference_6x6_v32.step

generate_gyroid_step.py:
  φ_gyroid_mm() → marching_cubes(φ, level=-t)
    → write_stl(임시 STL)
    → freecadcmd -c stl_to_step_freecad.py
         [STL_PATH, STEP_PATH, (DUCT_PATH=empty_duct_v32.step)]
    → gyroid_network_*.step  [, 동일 메쉬 기준 STL 저장 가능]
```

- **empty_duct_v32.step**은 `generate_gyroid_step.py --with-duct` 실행 시 선택적으로 사용되므로, 덕트 포함 자이로이드를 만들려면 먼저 `export_empty_duct_step.py`로 빈 덕트 STEP을 생성해 두는 것이 좋다.

---

## 3. 형상 수식 및 파라미터 (요약)

### 3.1 공통 도메인 (mm)

| 항목 | 값 | 비고 |
|------|-----|------|
| 외부 단면 | 25.4 × 25.4 | 1 inch |
| 외벽 두께 | 1.0 | |
| 내부 유로 단면 | 23.4 × 23.4 | 25.4 − 2×1.0 |
| 전체 Z | 110 | |
| 버퍼 Z | 0~5, 105~110 | Gyroid 없는 유체 영역 |
| 메인 Z | 5~105 | Gyroid 배치 구간 100 mm |

### 3.2 자이로이드 네트워크 (Network)

- **스칼라장** (단위 없음):
  - φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)
- **Solid(고체):** φ > −t  
- **Fluid(유체):** φ ≤ −t  
- **파라미터:** a [mm] 단위셀 크기(권장 3~8), t 두께(권장 0.05~0.5). 기본 a=5, t=0.3.
- **공극률 추정:** ε ≈ 0.5 + t/3 (예: t=0.3 → ε≈0.6).

자이로이드 메쉬는 **메인 구간만** (x,y,z ∈ [1, 24.4]×[1, 24.4]×[5, 105])에서 생성되며, STEP 변환 시 필요하면 빈 덕트와 fuse하여 외벽을 붙인다.

### 3.3 레퍼런스 6×6

- 채널 폭: CHANNEL_W = (23.4 − 5×1.0)/6 ≈ 3.067 mm  
- 한 셀 주기: PERIOD = CHANNEL_W + 1.0 mm  
- 메인 구간에 6×6 채널, 입출구 버퍼는 빈 유로.

---

## 4. 파이프라인 상세: generate_gyroid_step.py

### 4.1 처리 흐름

1. **격자 생성**  
   메인 구간을 `--res`(기본 60) 등분하여 3D 격자 생성.

2. **φ 계산**  
   `phi_gyroid_mm(X, Y, Z, a)`로 각 격자점에서 φ 계산.

3. **Marching cubes**  
   `level = -t`에서 등값면 추출 → 꼭짓점(verts)·면(faces). 인덱스 좌표를 mm로 변환.

4. **STL 작성**  
   `write_stl()`로 ASCII STL 생성.  
   - 기본 동작: 임시 파일에만 쓰고 FreeCAD 입력으로 사용 후 삭제.  
   - `--stl <경로>` 사용 시: 동일 메쉬를 해당 경로에 저장하여 시각적 검증용으로 활용.

5. **FreeCAD 호출**  
   환경변수 `STL_PATH`, `STEP_PATH`, (선택) `DUCT_PATH`를 설정하고  
   `freecadcmd -c "exec(open('stl_to_step_freecad.py').read())"` 실행.  
   - `stl_to_step_freecad.py`: STL → makeShapeFromMesh → removeSplitter → Solid → (DUCT_PATH 있으면 fuse) → STEP 내보내기.

6. **로깅**  
   파라미터, 수식, bbox, 면 수, 출력 STEP 파일 크기 출력.

### 4.2 명령줄 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--a` | 5.0 | 단위셀 크기 [mm], 3~8로 클리핑 |
| `--t` | 0.3 | 두께 파라미터 (solid = φ > -t), 0.05~0.5 |
| `--res` | 60 | Marching cubes 해상도, 30~120 |
| `--out` | (자동) | 출력 STEP 경로. 비우면 `gyroid_network_a{n}_t{mm}.step` |
| `--with-duct` | True | 빈 덕트 STEP과 fuse |
| `--no-duct` | — | 덕트 없이 자이로이드만 STEP |
| `--buffer` | 5.0 | 입출구 버퍼 길이 [mm] (도메인 정의와 일치) |
| `--stl` | (없음) | 지정 시 동일 메쉬를 해당 경로에 STL로 저장(시각적 검증용). STEP 생성 시 함께 저장. |
| `--stl-only` | False | STEP 없이 STL만 생성(FreeCAD 불필요). 빠른 시각 검증용. |

### 4.3 해상도별 가이드 (README 기준)

| --res | 용량/품질 | 비고 |
|-------|-----------|------|
| 30 | 작은 파일, 빠름 | 검증/테스트 |
| 60 | 중간 | 권장, 변환 수 분 소요 가능 |
| 120 | 큰 파일, 고해상도 | 고품질 형상 필요 시 |

---

## 5. FreeCAD 스크립트 상세

### 5.1 stl_to_step_freecad.py

- **입력:** 환경변수 `STL_PATH`, `STEP_PATH`, (선택) `DUCT_PATH` 또는 인자 `stl step [duct]`.
- **처리:**  
  - Mesh.Mesh(stl) → makeShapeFromMesh(0.1) → removeSplitter → Shell → Solid.  
  - DUCT_PATH가 있으면 해당 STEP을 읽어와서 solid와 fuse.  
  - 결과를 STEP으로 내보냄.
- **용도:** 자이로이드 메쉬를 B-Rep Solid로 바꾸고, 필요 시 빈 덕트와 합쳐 ANSYS 등에서 쓸 수 있는 STEP 생성.

### 5.2 export_empty_duct_step.py

- Part.makeBox로 외부 25.4×25.4×110, 내부 23.4×23.4×110 구멍 뚫어 덕트 형상 생성 후 STEP 내보내기.
- 출력: `empty_duct_v32.step`.

### 5.3 export_reference_6x6_step.py

- 동일 외곽·벽·버퍼에, 메인 구간에 6×6 채널 구멍을 B-Rep로 잘라냄.
- 출력: `reference_6x6_v32.step`.

---

## 6. 검증: verify_bbox.py

- **역할:** 전달용 STEP 3종(`empty_duct_v32.step`, `reference_6x6_v32.step`, `gyroid_network_a5_t03.step`) 존재 여부 및 파일 크기 확인.
- **bbox:** “명목 25.4×25.4×110 mm”를 출력하며, 실제 bbox는 ANSYS/SpaceClaim 등에서 import 후 확인하라고 안내.
- **환경변수:** `GEOMETRY_EXCHANGE_DIR`로 검사 디렉터리 지정 가능.

---

## 7. ANSYS 전달 시 유의사항 (README 요약)

- **Import:** File → Open으로 STEP 선택. Faceted(삼각 메쉬 기반)일 수 있으므로 **Facets → B-Surface** 변환 옵션 권장.
- **단위:** mm 기준으로 맞출 것.
- **전달 전 체크:** Body 수, Bounding box, Import 경고 메시지 확인.

---

## 8. LBM(Taichi)과의 대응

- Taichi 쪽 `set_geometry_gyroid_kernel(a, t, gyroid_type="network")`와 동일 수식·조건 사용.
- STP/연속 형상과 LBM voxel 형상은 격자 분할에 따라 경계 위치가 **약 ±0.5·dx** 정도 달라질 수 있음.

---

## 9. 시각적 검증용 STL 생성

### 9.1 3종 형상 STL 일괄 생성: `generate_all_stl.py`

`generate_all_stl.py`는 **FreeCAD 없이** 3종 형상 STL을 모두 생성하는 통합 스크립트이다.  
Taichi LBM 시뮬레이션과 동일한 **voxel 기반 marching cubes** 방식을 사용하므로, 시뮬레이션 형상과 직접 비교 가능하다.

| 출력 STL | 형상 | 설명 |
|----------|------|------|
| `empty_duct.stl` | 빈 덕트 | 외벽 1mm, 내부 빈 유로 (Z 관통) |
| `reference_6x6.stl` | 6×6 채널 | 메인 5~105mm에 36채널, 입출구 버퍼 |
| `gyroid_with_duct.stl` | 자이로이드+외벽 | Network gyroid + 외벽 1mm + 버퍼 |

**사용법:**

```bash
# 3종 모두 생성 (voxel 0.5mm)
python generate_all_stl.py

# 고해상도 (0.3mm)
python generate_all_stl.py --res 0.3

# 자이로이드만
python generate_all_stl.py --types gyroid

# 파라미터 변경
python generate_all_stl.py --a 5 --t 0.3 --res 0.5
```

**외벽 구현 방식:**  
- 시뮬레이션(`_init_gyroid_duct_kernel`)과 동일하게 `x < 1mm` 또는 `x > 24.4mm` (y도 동일) → 고체.  
- 버퍼 영역(z < 5mm, z > 105mm)에서는 외벽만 존재하고 내부는 빈 유로(유체).  
- 메인 영역(5~105mm)에서는 외벽 + 자이로이드(φ > -t) 고체.

### 9.2 generate_gyroid_step.py의 --stl 옵션

`generate_gyroid_step.py --stl` 또는 `--stl-only`는 **내부 자이로이드 메쉬만** 생성하며 외벽을 포함하지 않는다(STEP 변환 시 FreeCAD에서 덕트와 fuse).  
외벽까지 포함된 STL이 필요하면 **`generate_all_stl.py`** 를 사용한다.

---

## 10. 요약

| 항목 | 내용 |
|------|------|
| **프로젝트 성격** | ANSYS 전달용 STEP 형상 패키지 + 파라미터화 자이로이드 STEP/STL 생성 파이프라인 |
| **핵심 스크립트** | `generate_gyroid_step.py` (자이로이드 → STL → FreeCAD → STEP, 선택적 STL 저장) |
| **보조 스크립트** | `stl_to_step_freecad.py`, `export_empty_duct_step.py`, `export_reference_6x6_step.py`, `verify_bbox.py` |
| **문서** | `GEOMETRY_FORMULAS_AND_PARAMS.md`, `README_ANSYS_DELIVERY.md` |
| **STL 일괄 생성** | `generate_all_stl.py` — 3종(빈 덕트, 6×6, 자이로이드+외벽) STL, FreeCAD 불필요 |

이 보고서는 `geometry_exchange_ansys` 폴더의 구조, 수식, 파이프라인, 사용법, 검증 방법을 한곳에 정리한 종합 분석 문서이다.

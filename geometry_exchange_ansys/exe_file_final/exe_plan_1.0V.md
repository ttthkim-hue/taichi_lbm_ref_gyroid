# Gyroid Catalyst Support Generator — v4 종합 계획서

**최종 수정:** 2026-03-30
**버전:** v4 (STL auto-cap + Assembly STEP + decimation + buffer toggle)
**상태:** 구현 완료, CI 빌드 성공

> 상세 구현 기록: [v4_implementation_details.md](v4_implementation_details.md)

---

## 0. 파일 구조

```
gyroid_generator/
  gyroid_gui.py                  ← 메인 GUI (857 lines)
  step_converter_assembly.py     ← STEP 변환 subprocess (200 lines)
  GyroidGenerator.spec           ← PyInstaller 설정 (108 lines)
  build_exe.py                   ← 수동 빌드 스크립트
  requirements.txt
  delivery_package/
    GyroidGenerator_v4/          ← 최종 배포 (~555 MB)
      GyroidGenerator.exe        ← GUI (16 MB)
      step_converter_assembly.exe← STEP 변환기 (16 MB)
      _internal/                 ← Python + OCP + numpy 등

.github/workflows/
  build-gyroid-generator-windows.yml  ← CI/CD (155 lines)
```

---

## 1. 고정 규격 (변경 금지)

| 항목 | 값 | 비고 |
|------|-----|------|
| 덕트 외경 | 25.4 x 25.4 mm | 1인치 정사각 |
| 덕트 벽두께 | 1.0 mm | |
| 덕트 내경 | 23.4 mm | `DUCT_OUTER - 2*DUCT_WALL` |
| 총 Z 길이 | 110.0 mm | |
| 벽 침투(overlap) | 0.3 mm | 자이로이드-덕트벽 |
| 자이로이드 XY 도메인 | 24.0 mm | `23.4 + 2*0.3` |
| XY 시작/끝 | 0.7 / 24.7 mm | `(25.4-24.0)/2` |

---

## 2. 핵심 수식

### 2.1 자이로이드 스칼라 필드

```
phi(x,y,z) = sin(kx)cos(ky) + sin(ky)cos(kz) + sin(kz)cos(kx)
k = 2*pi/a
Solid: phi > -t
```

### 2.2 레이아웃 계산

**Z 레이아웃** (`calc_z_layout`):
```python
# use_buffer=True (기본): 앞뒤 최소 5mm 빈 덕트
max_gyroid_z = 110.0 - 2 * min_duct   # min_duct=5.0 (fallback 4.0)
n_cells_z = int(max_gyroid_z // a)

# use_buffer=False: 자이로이드 Z 최대화
n_cells_z = int(110.0 // a)
buffer = (110.0 - n_cells_z * a) / 2  # 중앙 정렬
```

**XY 레이아웃**: `n_cells_xy = round(24.0 / a)`, 정합값: 3,4,6,8,12,24 mm

**정합값 레이아웃 테이블:**

| a [mm] | XY cells | Z cells (buf ON/OFF) | Total cells |
|--------|----------|----------------------|-------------|
| 4 | 6 | 25 / 27 | 900 / 972 |
| 6 | 4 | 16 / 18 | 256 / 288 |
| 8 | 3 | 12 / 13 | 108 / 117 |
| 12 | 2 | 8 / 9 | 32 / 36 |
| 24 | 1 | 4 / 4 | 4 / 4 |

### 2.3 STL 크기 추정 & auto-cap

```python
SA = 3.1/a * 24^2 * n_cells_z * a    # 자이로이드
   + 4 * 25.4 * 110                   # 덕트 외벽
   + 4 * 23.4 * 110                   # 덕트 내벽

faces ~ 2 * SA * res^2 / a^2         # marching_cubes 출력
res_cap = sqrt(199998 * a^2 / (2*SA)) # 10MB 역산
res = min(user_input, res_cap)        # 최종 적용
```

**a별 res_cap**: 4mm→5, 8mm→12, 12mm→21, 24mm→57

### 2.4 최소 벽두께 측정

```python
# 2x2x2 periodic tiling + distance_transform_edt + medial axis
min_wall = dt[ridge].min() * 2        # 직경 = 2 * 반경
```

---

## 3. 복셀 필드 합성 (mesh boolean 대체)

```python
phi = gyroid_phi(x, y, z)
# 덕트 밖 → -10 (void) / 덕트벽 4면 → +10 (solid)
# 앞뒤 버퍼 내부 → -10 (void) / 자이로이드 영역 → 자연 phi
marching_cubes(phi, level=-t) → watertight mesh
# 후처리: simplify_quadric_decimation(50%)
```

메모리 보호: `MAX_VOXELS=150M` 초과 시 grid 자동 축소

---

## 4. STEP 생성 (ISO 10303-214)

### v2-v3 문제 (해결됨)
- `STEPCAFControl_Writer` + XCAF: Transfer 실패, 뷰어 미지원

### v4 방식 (현재)
```python
cell_shape = _make_unit_cell_ocp(a, t, res_cell)  # ~500 faces (decimated)

compound = TopoDS_Compound()
for grid_position:
    located = cell_shape.Moved(TopLoc_Location(trsf))  # TShape 공유
    builder.Add(compound, located)
builder.Add(compound, duct_wall)  # B-rep solid

writer = STEPControl_Writer()     # 단순 Writer (모든 뷰어 호환)
writer.Transfer(compound, STEPControl_AsIs)
writer.Write(output_path)
```

---

## 5. GUI 구성

| 파라미터 | 기본값 | 범위 |
|----------|--------|------|
| a [mm] | 4.0 | 3~30 |
| t | 0.10 | 0.01~0.50 |
| STL res | 60 | 5~120 (auto-cap) |
| STEP cell res | 10 | 8~40 |
| 외벽 포함 | ON | |
| 앞뒤 버퍼 | ON | OFF→Z 최대화 |

**출력**: STL(10MB cap+50% decimate), STEP(AP214), 단위셀 STL, 단면 STL

---

## 6. 빌드 & CI

- PyInstaller onedir: GUI EXE + STEP EXE + _internal
- GitHub Actions: syntax check (Ubuntu) → build (Windows) → artifact upload
- Python 3.12, cadquery (OCP), 45min timeout

---

## 7. 버전 이력

| 버전 | 날짜 | 변경 |
|------|------|------|
| v1 | 03-19 | 초기 계획, mesh boolean |
| v2 | 03-29 | 복셀 필드 합성, boolean 제거, 한글 UI |
| v3 | 03-30 | a 확장(30mm), Assembly STEP(XCAF) |
| **v4** | **03-30** | **STL auto-cap+decimation, STEP STEPControl fix, buffer toggle** |

**사용자 지시사항(엄수)**
# Gyroid Generator 문제 분석 및 해결 지시사항

**작성일:** 2026-03-30  
**대상 프로그램:** Gyroid STL/STEP Generator (Streamlit 또는 Colab 노트북)  
**현재 상태:** 3건 미해결 — 버퍼 OFF 모드, STL 용량, STEP 뷰어 호환성

---

## 문제 1: 버퍼 OFF 시 자이로이드만 100mm로 생성되어야 함

### 동작 정의

| 모드 | 자이로이드 Z | 빈 덕트 버퍼 | 총 Z 길이 | 외벽 |
|------|------------|-------------|----------|------|
| **ON** (기본) | 100mm 구간 (a 정수배, 중앙정렬) | 앞 5mm + 뒤 5mm | **110mm** | 0~110mm 전체 |
| **OFF** | 100mm 구간 (a 정수배, 중앙정렬) | **없음** | **≈100mm** (a 정수배) | 자이로이드 구간만 |

핵심: **자이로이드 목표 길이는 항상 100mm**. 차이는 앞뒤 빈 덕트 버퍼(5mm×2)의 유무.

### 증상

- OFF 설정 시, 자이로이드가 100mm가 아닌 다른 길이로 생성됨
- 또는 OFF인데도 여전히 총 110mm (버퍼 포함) 구조로 출력됨
- 또는 자이로이드는 100mm인데 외벽이 110mm로 남아 앞뒤에 빈 공간 발생

### 근본 원인

현재 코드에서 Z 범위와 총 길이가 `TOTAL_Z = 110.0`에 하드코딩되어 있음:

```python
# 기존 코드 (문제)
TOTAL_Z = 110.0
BUFFER = 5.0
MAIN_START = BUFFER          # 항상 5.0
MAIN_END = TOTAL_Z - BUFFER  # 항상 105.0

# 체크박스 OFF여도 외벽/전체 도메인은 110mm 고정
# → 자이로이드 100mm + 양쪽 빈 공간 5mm = 사실상 버퍼 ON과 동일
```

### 해결 방법

```python
# ── 상수 ──
DUCT_OUTER = 25.4       # mm, 1인치
WALL = 1.0              # mm
GYROID_TARGET_Z = 100.0  # mm, 자이로이드 목표 길이 (ON/OFF 공통)
BUFFER_EACH = 5.0        # mm, 앞뒤 버퍼 각각

def generate_gyroid_mesh(a_mm, t, res, use_buffer=True):
    """
    자이로이드는 항상 100mm 기준 (a의 정수배, 중앙정렬).
    
    use_buffer=True:
        총 길이 = 110mm
        자이로이드 구간 = [5 + offset, 5 + offset + L_gyroid]
        앞뒤 5mm는 빈 덕트 (유체만)
        
    use_buffer=False:
        총 길이 = L_gyroid (≤ 100mm, a의 정수배)
        자이로이드 구간 = [0, L_gyroid]
        빈 덕트 없음, 외벽도 L_gyroid에 맞춤
    """
    x_min, x_max = WALL, DUCT_OUTER - WALL  # 1.0 ~ 24.4

    # ── 자이로이드 Z 길이 계산 (공통) ──
    n_cells_z = int(GYROID_TARGET_Z / a_mm)     # floor(100 / a), 정수배
    L_gyroid = n_cells_z * a_mm                  # 실제 자이로이드 길이
    remainder = GYROID_TARGET_Z - L_gyroid       # 나머지 (중앙정렬용)

    if use_buffer:
        # ON: 총 110mm, 자이로이드는 중앙 100mm 구간 내 중앙정렬
        total_z = GYROID_TARGET_Z + 2 * BUFFER_EACH  # 110mm
        gyroid_z_start = BUFFER_EACH + remainder / 2.0
        gyroid_z_end = gyroid_z_start + L_gyroid
    else:
        # OFF: 자이로이드만, 총 길이 = L_gyroid
        total_z = L_gyroid                       # 버퍼 없음
        gyroid_z_start = 0.0
        gyroid_z_end = L_gyroid

    # ── marching cubes ──
    nz = max(20, int(L_gyroid / a_mm * res))
    z = np.linspace(gyroid_z_start, gyroid_z_end, nz)
    # ... 이하 동일

    return verts, faces, eps, {
        'total_z': total_z,
        'gyroid_z': (gyroid_z_start, gyroid_z_end),
        'L_gyroid': L_gyroid,
        'n_cells_z': n_cells_z,
    }
```

### 외벽 결합 시 주의

```python
if use_buffer:
    # 외벽 박스: 25.4 × 25.4 × 110mm
    duct_z_length = total_z  # 110mm
else:
    # 외벽 박스: 25.4 × 25.4 × L_gyroid mm
    duct_z_length = L_gyroid  # ← 110mm가 아님!
```

### a별 동작 예시

| a [mm] | floor(100/a) | L_gyroid [mm] | 나머지 | OFF 시 총 Z | ON 시 자이로이드 구간 |
|--------|-------------|---------------|--------|------------|---------------------|
| 3 | 33 | 99 | 1.0 | 99mm | 5.5 ~ 104.5 mm |
| 5 | 20 | 100 | 0 | 100mm | 5.0 ~ 105.0 mm |
| 7 | 14 | 98 | 2.0 | 98mm | 6.0 ~ 104.0 mm |
| 8 | 12 | 96 | 4.0 | 96mm | 7.0 ~ 103.0 mm |

### 핵심 체크포인트

| 항목 | 확인 사항 |
|------|-----------|
| `use_buffer` 전달 | Streamlit 체크박스 값 → `generate_gyroid_mesh()` → 외벽 결합 함수까지 |
| OFF 시 총 Z | `trimesh.bounds`로 확인: Z 범위 = L_gyroid (100mm 이하), 110mm면 실패 |
| OFF 시 외벽 | 외벽 Z 길이가 L_gyroid와 동일한지 (110mm 아님) |
| ON 시 버퍼 구간 | Z = 0~5mm, 105~110mm 구간에 자이로이드 없이 빈 덕트만 있는지 |
| 정보 패널 | "총 길이: {total_z}mm / 자이로이드: {L_gyroid}mm / 버퍼: {'5mm×2' if ON else '없음'}" |

### 흔한 실수

1. **OFF인데 외벽이 110mm** — 자이로이드는 100mm인데 외벽 박스가 `TOTAL_Z=110` 고정 → 앞뒤 빈 공간 = 사실상 버퍼 ON
2. **OFF인데 `total_z` 반환값이 110** — STEP/STL bounding box가 110mm → 뷰어에서 빈 구간 보임
3. **체크박스 미전달** — UI만 바뀌고 내부 로직은 항상 `use_buffer=True`로 동작

---

## 문제 2: STL 용량이 10MB 이상

### 증상

- `simplify_quadric_decimation(50%)` 적용 계획이었으나 실제 파일이 여전히 10MB 초과
- 또는 decimation 적용 자체가 실패/무시됨

### 근본 원인 분석

STL 용량은 **면(face) 수에 비례**함. binary STL 기준 면당 50 bytes.

```
현재 상태 추정:
  res=60, a=5mm, 도메인 23.4×23.4×100mm
  → 격자: ~280×280×1200 ≈ 94M points
  → marching cubes 면 수: ~200k~500k
  → 500k faces × 50 bytes = 25MB
```

#### 원인 A: decimation이 적용 안 됨

```python
# 흔한 실수: trimesh의 simplify_quadric_decimation은 open3d 또는 별도 backend 필요
mesh = trimesh.Trimesh(vertices=verts, faces=faces)
mesh_simplified = mesh.simplify_quadric_decimation(len(faces) // 2)  
# ↑ trimesh에 이 메서드가 없거나, 내부적으로 실패해도 예외 안 던짐
```

trimesh의 `simplify_quadric_decimation`은 **open3d backend가 설치되어야** 동작함. 없으면 silent fail하거나 원본 반환.

#### 원인 B: 해상도(res)가 과도

res=60이면 단위셀당 60³ = 216,000 격자점. a=5mm에 도메인 23.4mm면 ~4.7개 단위셀, Z 방향 20개 → 총 격자점 수천만.

#### 원인 C: decimation 후에도 외벽 메쉬가 별도로 추가됨

자이로이드 decimation 후, 외벽 박스 메쉬를 union하면서 면 수가 다시 증가.

### 해결 방법 (3단계 조합)

#### 2-1. 해상도 auto-cap (가장 효과적)

```python
# 목표: 최종 STL ≤ 5MB → 면 수 ≤ 100,000
MAX_FACES = 100_000

# 해상도를 면 수 기준으로 자동 조절
def auto_res(a_mm, target_faces=MAX_FACES):
    """
    면 수 ≈ 2 * (n_cells_xy * res)^2 * n_cells_z * res * surface_ratio
    경험적으로 res와 면 수는 res^2.5 ~ res^3 관계
    """
    # 보수적 시작: res=30에서 면 수 측정 후 스케일링
    # 또는 하드 리밋:
    if a_mm <= 3:
        return min(res, 30)   # 작은 단위셀 → 반복 많음 → 저해상도
    elif a_mm <= 5:
        return min(res, 40)
    else:
        return min(res, 50)
```

#### 2-2. Quadric decimation (open3d 사용)

```python
import open3d as o3d

def decimate_mesh(verts, faces, target_ratio=0.5):
    """
    open3d의 quadric decimation 사용.
    trimesh 단독으로는 안정적인 decimation이 어려움.
    """
    mesh_o3d = o3d.geometry.TriangleMesh()
    mesh_o3d.vertices = o3d.utility.Vector3dVector(verts)
    mesh_o3d.triangles = o3d.utility.Vector3iVector(faces)

    target_faces = int(len(faces) * target_ratio)
    mesh_simplified = mesh_o3d.simplify_quadric_decimation(target_faces)

    verts_out = np.asarray(mesh_simplified.vertices)
    faces_out = np.asarray(mesh_simplified.triangles)
    return verts_out, faces_out
```

**주의:** Colab에서 `pip install open3d`는 정상 동작. 로컬 환경에서도 문제 없음.

#### 2-3. 파이프라인 순서

```python
# 1. Gyroid 생성 (해상도 cap 적용)
effective_res = auto_res(a_mm)
verts, faces, eps = generate_gyroid_mesh(a_mm, t, effective_res, use_buffer)

# 2. Decimation (원본 면 수의 50%)
try:
    verts, faces = decimate_mesh(verts, faces, target_ratio=0.5)
    print(f"Decimation: {len(faces)} faces")
except Exception as e:
    print(f"Decimation 실패, 원본 유지: {e}")

# 3. 외벽 결합 (외벽은 면 수 매우 적음, ~12 faces)
combined = combine_with_duct(verts, faces, ...)

# 4. STL 저장
combined.export(filename, file_type='stl')
size_mb = os.path.getsize(filename) / 1024 / 1024
print(f"STL: {size_mb:.1f} MB, {len(combined.faces)} faces")
```

### 용량 예측표

| res | decimation | 예상 면 수 | 예상 크기 |
|-----|-----------|-----------|----------|
| 60  | 없음      | ~400k     | ~20 MB   |
| 60  | 50%       | ~200k     | ~10 MB   |
| 40  | 없음      | ~120k     | ~6 MB    |
| 40  | 50%       | ~60k      | ~3 MB    |
| 30  | 50%       | ~30k      | ~1.5 MB  |

**권장:** res=40 + decimation 50% → **약 3MB** (ANSYS import에 충분한 품질)

---

## 문제 3: STEP 파일 1.6MB인데 알씨캐드뷰어에서 안 열림, ANSYS 호환 불가

### 증상

- STEP 파일 생성됨 (1.6MB, 빈 껍데기는 아님)
- 알씨캐드뷰어(알캐드, eDrawings 등)에서 열리지 않음
- ANSYS SpaceClaim에서도 Import 실패 또는 비정상 렌더링

### 근본 원인

#### 원인 A: STEPCAFControl_Writer + XCAF document 사용

```python
# 기존 코드 (문제)
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDocStd import TDocStd_Document

doc = TDocStd_Document("XmlOcaf")
shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
# ... shape_tool.AddShape(shape)

writer = STEPCAFControl_Writer()
writer.Transfer(doc)       # ← 반환값 False (Transfer 실패)
writer.Write("output.step")
```

**문제점:**

1. `STEPCAFControl_Writer.Transfer(doc)` 반환값이 `False` → 형상이 STEP에 기록되지 않음
2. XCAF document는 PRODUCT_DEFINITION 계층 구조(NAUO: Next Assembly Usage Occurrence)를 생성하는데, 많은 뷰어가 이 구조를 지원하지 않음
3. 결과 STEP에 형상 엔티티는 있지만, 뷰어가 해석하지 못하는 어셈블리 참조 방식으로 기록됨

#### 원인 B: 면 수가 너무 많아 STEP 파일 구조 비대

STL의 각 삼각형이 STEP에서 개별 `ADVANCED_FACE` + `FACE_BOUND` + `EDGE_LOOP`로 변환됨.
면 수 N개 → STEP 엔티티 약 10N~15N개.

```
200k faces → ~2M~3M 엔티티 → 수십~수백 MB STEP
→ 1.6MB라면 면 수는 적지만, 구조가 잘못된 것
```

#### 원인 C: 인스턴싱 방식의 비호환

XCAF의 `NAUO`(Next Assembly Usage Occurrence)로 단위셀을 반복 배치하면, STEP 파일 크기는 줄지만 뷰어 호환성이 크게 떨어짐. FreeCAD, ANSYS, eDrawings 중 NAUO 기반 인스턴싱을 올바르게 해석하는 뷰어는 소수.

### 해결 방법: STEPControl_Writer + Moved() 인스턴싱

#### 핵심 전략 변경

```
기존: STEPCAFControl_Writer + XCAF document + NAUO 인스턴싱
     → Transfer(doc) 실패, 뷰어 비호환

변경: STEPControl_Writer + compound of Moved() instances
     → 모든 뷰어 호환, TShape 공유로 파일 크기 최소화
```

#### 구현 코드

```python
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing

def create_step_with_instancing(unit_cell_shape, positions, output_path):
    """
    단위셀 1개의 TShape를 공유하고, Moved()로 위치만 변경하여
    STEP 파일 크기를 최소화하면서 모든 뷰어 호환성 확보.

    Args:
        unit_cell_shape: TopoDS_Shape (단위셀 sewed shell)
        positions: list of (dx, dy, dz) 이동 벡터
        output_path: STEP 파일 경로
    """
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    for (dx, dy, dz) in positions:
        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(dx, dy, dz))
        loc = TopLoc_Location(trsf)
        # Moved(): 동일 TShape 공유, 위치만 다름
        moved = unit_cell_shape.Moved(loc)
        builder.Add(compound, moved)

    # STEP 저장 (STEPControl_Writer — 단순, 호환성 최고)
    writer = STEPControl_Writer()
    Interface_Static.SetCVal_s("write.step.schema", "AP214")
    Interface_Static.SetIVal_s("write.step.assembly", 0)  # flat structure

    status = writer.Transfer(compound, STEPControl_AsIs)
    if not status:
        raise RuntimeError("STEP Transfer 실패")

    write_status = writer.Write(output_path)
    if write_status != 1:
        raise RuntimeError(f"STEP Write 실패: status={write_status}")

    return output_path
```

#### 단위셀 준비 (decimation 후 sewing)

```python
def prepare_unit_cell(verts, faces, a_mm, target_faces=500):
    """
    단위셀 1개만 생성 → decimation → sewing → TopoDS_Shape 반환
    
    목표: 단위셀당 ~500 faces (기존 ~5000에서 90% 감소)
    전체 STEP 크기: TShape 1개 공유 → 단위셀 수에 거의 무관
    """
    import open3d as o3d

    # 1. 단위셀 1개 영역만 추출 (z ∈ [z_start, z_start + a_mm])
    # (또는 별도로 단위셀 해상도로 생성)

    # 2. Decimation
    mesh_o3d = o3d.geometry.TriangleMesh()
    mesh_o3d.vertices = o3d.utility.Vector3dVector(verts)
    mesh_o3d.triangles = o3d.utility.Vector3iVector(faces)
    mesh_simplified = mesh_o3d.simplify_quadric_decimation(target_faces)

    # 3. OCC Shape 변환
    # simplified mesh → STL 임시 저장 → StlAPI_Reader로 읽기
    # 또는 직접 BRepBuilderAPI_MakePolygon + Sewing

    # 4. Sewing
    sewing = BRepBuilderAPI_Sewing(0.01)  # tolerance 작게
    sewing.Add(stl_shape)
    sewing.Perform()
    unit_cell = sewing.SewedShape()

    return unit_cell
```

#### 전체 파이프라인

```python
def generate_step(a_mm, t, res, use_buffer, output_path):
    """
    1. 단위셀 1개 생성 (marching cubes, 해상도 cap)
    2. Decimation (~500 faces)
    3. Sewing → TopoDS_Shape
    4. 격자 위치 계산 (n_x × n_y × n_z 배열)
    5. Moved() 인스턴싱 → Compound
    6. 외벽 추가 (B-Rep 직접 생성, Boolean 불필요)
    7. STEPControl_Writer로 저장
    """
    # Z 범위 결정
    if use_buffer:
        z_start, z_end = 5.0, 105.0
    else:
        n_z = int(110.0 / a_mm)
        L = n_z * a_mm
        offset = (110.0 - L) / 2.0
        z_start, z_end = offset, offset + L

    x_min, x_max = WALL, DUCT_OUTER - WALL  # 1.0 ~ 24.4
    inner = x_max - x_min  # 23.4

    n_x = int(inner / a_mm)  # X 방향 단위셀 수
    n_y = n_x                # Y = X (정사각형)
    n_z = int((z_end - z_start) / a_mm)

    # 단위셀 1개 생성
    unit_verts, unit_faces, eps = generate_single_unit_cell(a_mm, t, res)
    unit_cell = prepare_unit_cell(unit_verts, unit_faces, a_mm, target_faces=500)

    # 위치 목록 (중앙 정렬)
    x_offset = x_min + (inner - n_x * a_mm) / 2.0
    y_offset = x_offset
    z_offset = z_start

    positions = []
    for ix in range(n_x):
        for iy in range(n_y):
            for iz in range(n_z):
                dx = x_offset + ix * a_mm
                dy = y_offset + iy * a_mm
                dz = z_offset + iz * a_mm
                positions.append((dx, dy, dz))

    # STEP 생성
    create_step_with_instancing(unit_cell, positions, output_path)

    return output_path
```

### STEP 크기 예측

| 항목 | 기존 | 수정 후 |
|------|------|---------|
| Writer | STEPCAFControl (XCAF) | STEPControl (simple) |
| 인스턴싱 | NAUO (미지원 다수) | Moved() (TShape 공유) |
| 단위셀 면 수 | ~5000 | ~500 (decimated) |
| 뷰어 호환 | 안 열림 | ANSYS, FreeCAD, eDrawings, 알씨캐드뷰어 |
| 예상 크기 | 1.6MB (깨진 구조) | ~200KB~500KB (정상) |

### 뷰어 호환성 검증 체크리스트

| 뷰어 | 확인 |
|------|------|
| ANSYS SpaceClaim | ☐ Import → 25.4×25.4×110mm 확인 |
| FreeCAD | ☐ File → Open → 형상 정상 렌더링 |
| eDrawings | ☐ 열림 확인 |
| 알씨캐드뷰어 | ☐ 열림 확인 |
| STEP 엔티티 수 | ☐ `grep -c "=" output.step` → 수천~만 단위 (수십만 아님) |

---

## 종합 수정 순서

```
Step 1: 해상도 auto-cap 적용 (res=40 기본값)
        → STL 면 수 1차 감소

Step 2: open3d quadric decimation 50% 적용
        → STL 면 수 2차 감소
        → try/except로 실패 시 원본 유지

Step 3: 버퍼 on/off 로직 수정
        → 자이로이드 목표 길이는 항상 100mm (a 정수배, 중앙정렬)
        → ON: 총 110mm (앞뒤 5mm 빈 덕트 버퍼)
        → OFF: 총 ≈100mm (자이로이드만, 버퍼/외벽 길이도 L_gyroid에 맞춤)
        → 정보 패널에 실시간 반영

Step 4: STEP Writer 교체
        → STEPCAFControl → STEPControl
        → 단위셀 Moved() 인스턴싱
        → 단위셀 decimation (~500 faces)

Step 5: 통합 테스트
        → STL: ≤ 5MB, bounding box 정확
        → STEP: ≤ 500KB, 4개 뷰어 모두 열림
        → 버퍼 OFF: 총 Z = floor(100/a)*a mm, 자이로이드만 (빈 덕트 없음)
```

---

## 의존성 추가

```
# requirements.txt에 추가
open3d           # quadric decimation용
cadquery         # OCC backend (STEPControl_Writer 포함)
```

Colab: `pip install open3d cadquery`  
로컬: 동일

---

## 디버그 출력 (생성 시 항상 표시)

```python
print(f"=== 생성 결과 ===")
print(f"버퍼: {'ON (5~105mm)' if use_buffer else 'OFF (Z 최대화)'}")
print(f"Gyroid Z 구간: {z_min:.1f} ~ {z_max:.1f} mm ({z_max-z_min:.1f} mm)")
print(f"단위셀: {n_x}×{n_y}×{n_z} = {n_x*n_y*n_z}개")
print(f"해상도: res={effective_res} (입력 {res}, cap 적용)")
print(f"STL 면 수: {len(faces):,} → decimation 후 {len(faces_dec):,}")
print(f"STL 크기: {stl_size_mb:.1f} MB")
print(f"STEP Writer: STEPControl_Writer (simple, 호환)")
print(f"STEP 크기: {step_size_mb:.2f} MB")
print(f"Bounding box: {bbox}")
```
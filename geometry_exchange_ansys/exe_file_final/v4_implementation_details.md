# v4 상세 구현 기록

**참조:** [exe_plan_1.0V.md](exe_plan_1.0V.md) (계획서 본문)

---

## A. STL 10MB Auto-Cap 구현

### 근본 문제 (v3)
```
res = max(30, ...) 바닥 → a=4mm에서 필요한 res=5 도달 불가
표면적 과소추정: 덕트 내벽 SA 누락
→ 생성된 STL = 200MB (목표 10MB)
```

### 수정 (`gyroid_gui.py`)

**함수 `_estimate_sa(a, n_cells_z)`** (line 53-58):
```python
sa_gyroid = 3.1 / a * GYROID_DOMAIN_XY**2 * n_cells_z * a  # TPMS surface
sa_duct_outer = 4.0 * DUCT_OUTER * TOTAL_Z                  # 4 outer walls
sa_duct_inner = 4.0 * DUCT_INNER * TOTAL_Z                  # 4 inner walls
return sa_gyroid + sa_duct_outer + sa_duct_inner
```

**함수 `calc_max_res_for_stl(a, n_cells_z)`** (line 61-67):
```python
res_max = (MAX_STL_FACES * a**2 / (2.0 * sa)) ** 0.5
return max(5, int(res_max))           # 바닥 5 (v3: 20)
```

**`do_generate`에서 적용** (line 747-750):
```python
res_cap = calc_max_res_for_stl(a, layout["n_cells_z"])
res = min(res_input, res_cap)          # auto-cap
```

---

## B. STL 50% Decimation 구현

### 메서드 `_decimate(mesh, ratio=0.5)` (line 428-438):
```python
target = max(100, int(len(mesh.faces) * ratio))
try:
    reduced = mesh.simplify_quadric_decimation(target)
    if len(reduced.faces) > 0:
        return reduced
except Exception:
    pass                               # 실패 시 원본 반환
return mesh
```

적용 위치: 원본 STL (line 789), 단면 STL (line 815)

---

## C. STEP 뷰어 호환성 수정

### 문제 분석 (v3 XCAF 방식)

| 구성요소 | 상태 | 문제 |
|----------|------|------|
| `XCAFApp_Application` | OK | 문서 초기화 정상 |
| `shape_tool.AddShape` | OK | 셀 등록 정상 |
| `shape_tool.AddComponent` | OK | 인스턴스 배치 정상 |
| `STEPCAFControl_Writer.Transfer(doc)` | **False** | XCAF→STEP 직렬화 실패 |
| STEP 파일 | 생성됨 (13MB) | 뷰어에서 열리지 않음 |

**원인**: OCP의 `STEPCAFControl_Writer`가 XCAF assembly 구조를 STEP AP214의 `NEXT_ASSEMBLY_USAGE_OCCURENCE` 엔티티로 올바르게 변환하지 못함. 일부 OCP 빌드에서 Transfer가 False를 반환하며, 생성된 STEP의 product structure가 불완전.

### 해결 (v4): `STEPControl_Writer` + `Moved()`

```python
# step_converter_assembly.py (완전 재작성)

# 1. 단위셀: marching_cubes → decimate(500 faces) → sewing
cell_shape, n_faces = _make_unit_cell_ocp(a, t, res_cell)

# 2. Compound: Moved()로 N개 배치
compound = TopoDS_Compound()
for position in grid:
    located = cell_shape.Moved(TopLoc_Location(trsf))
    # Moved(): 동일 TShape 참조, Location만 다름
    # → STEP writer가 공유 topology 인식 가능
    builder.Add(compound, located)

# 3. 덕트벽: 진짜 B-rep solid (MakeBox - Cut)
wall = BRepAlgoAPI_Cut(outer, inner).Shape()
builder.Add(compound, wall)

# 4. 단순 Writer (모든 뷰어 호환)
writer = STEPControl_Writer()
writer.Transfer(compound, STEPControl_AsIs)
status = writer.Write(out_path)        # status=1: 성공
```

**XCAF vs STEPControl 비교:**

| 항목 | XCAF (v3) | STEPControl (v4) |
|------|-----------|------------------|
| Transfer 성공률 | 불안정 | 100% |
| 뷰어 호환 | 낮음 | 모든 뷰어 |
| Assembly 구조 | NAUO | Compound |
| 파일 크기 | 이론적 최소 | Moved() 공유 의존 |
| 복잡도 | XCAF doc 관리 | 단순 |

---

## D. 앞뒤 버퍼 On/Off

### `calc_z_layout(use_buffer)` 분기:

```python
if use_buffer:
    # 기존 로직: min_duct=5mm (fallback 4mm)
    max_gyroid_z = total_z - 2 * min_duct
else:
    # 버퍼 없음: 전체 110mm에서 a의 정수배 최대
    n_cells_z = int(total_z // a)
    # 남는 공간은 중앙 정렬
```

**a=4mm 예시:**
- buffer ON: 25 cells, buffer=5.0mm
- buffer OFF: 27 cells, buffer=1.0mm (110-108=2, 1mm씩)

---

## E. 인코딩 수정

| 위치 | 수정 |
|------|------|
| `step_converter_assembly.py` print | 전체 영어 (Windows cp949 안전) |
| `convert_to_step_assembly` Popen | `env={"PYTHONIOENCODING": "utf-8"}` |
| subprocess 출력 디코딩 | `decode("utf-8", errors="replace")` |

---

## F. 삭제된 코드 (v4에서 제거)

| 항목 | 이유 |
|------|------|
| `step_converter.py` | mesh 기반 STEP (수백 MB) → Assembly 방식으로 대체 |
| `_find_converter()` | old step_converter 경로 탐색 |
| `convert_to_step()` | old STL→STEP 호출 |
| `self.step_var` | old STEP 체크박스 |
| `self.step_res_var` | old STEP 해상도 |
| `step_exe` in .spec | old step_converter EXE |

---

## G. 파일 경로 인덱스

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `gyroid_gui.py` | 857 | 메인 GUI + STL 생성 |
| `step_converter_assembly.py` | 200 | STEP subprocess |
| `GyroidGenerator.spec` | 108 | PyInstaller 설정 |
| `build-gyroid-generator-windows.yml` | 155 | CI/CD |
| `exe_plan_1.0V.md` | ~120 | 계획서 (본 파일이 상세) |

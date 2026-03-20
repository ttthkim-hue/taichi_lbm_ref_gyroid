# Gradient_Smooth_Fine.stl 생성 코드 조사 및 Taichi 수식 비교

## 1. Gradient_Smooth_Fine.stl 생성 경로

- **파일**: `.../260107_Taichi_LBM/09_Archived_Results/archive_v1_20260219/1inch_ScaleUp_Project/04_Report/STL_Printable/Gradient_Smooth_Fine.stl`
- **생성 스크립트**: 같은 폴더의 **`generate_batch_printable_stls.py`**
- **입력 지오메트리**: `01_Geometry/Gyroid_1inch_Gradient_Smooth.npy` (voxel 마스크)

---

## 2. 외벽이 잘 구현된 이유 (막힌 1 mm 벽)

`generate_batch_printable_stls.py`는 **외벽을 voxel/marching cubes에 전혀 의존하지 않고**, PyVista의 **기하 연산만**으로 만듭니다.

```python
# 1. Create Geometric Casing (Exact Primitive)
outer = pv.Cube(center=(dim_x/2, dim_y/2, dim_z/2), x_length=dim_x, y_length=dim_y, z_length=dim_z)
inner = pv.Cube(
    center=(dim_x/2, dim_y/2, dim_z/2),
    x_length=dim_x - 2*WALL_MM,   # 1mm 벽
    y_length=dim_y - 2*WALL_MM,
    z_length=dim_z + 2.0
)
casing = outer.triangulate().boolean_difference(inner.triangulate())

# 2. Gyroid Mesh (Marching Cubes from .npy)
padded = np.pad(mask, 1, mode='constant', constant_values=0)
grid = pv.ImageData(); ...
gyroid = grid.contour([0.5], scalars='v', method='marching_cubes')

# 3. Merge (단순 메쉬 append, boolean 아님)
merged = casing + gyroid
merged.save(out_path)
```

- **외벽**: `outer - inner` boolean difference → **항상 1.0 mm 두께의 막힌 솔리드 벽**.
- **자이로이드**: .npy 마스크에서 marching cubes로 표면만 추출.
- **병합**: 두 메쉬를 **그냥 더함**(append). 외벽은 casing만 쓰므로 **외벽에 구멍이 날 여지가 없음**.

우리 쪽에서 동일한 방식을 쓰려면:

- **외벽**: OpenSCAD `empty_duct_v32.stl` (또는 PyVista 등으로 동일하게 outer−inner 박스)만 사용.
- **자이로이드**: 수식/마스크에서 marching cubes로 **자이로이드만** STL 생성.
- **최종**: 두 STL을 **voxel 단계에서 union**하거나, 한 STL로 쓰려면 두 메쉬를 **append** (Gradient_Smooth_Fine과 동일한 방식).

---

## 3. 자이로이드 수식 비교

### 3.1 Gradient_Smooth (Gradient_Smooth_Fine용 .npy 생성)

**스크립트**: `01_Geometry/generate_gyroid_smooth.py`

- **도메인**: dx=0.4 mm, 25.4×25.4×**100** mm (Z 버퍼는 마스크에서 5 voxel씩 0으로 만듦).
- **Z 방향 변수**:
  - `L_profile(z)`: 14.0 → 10.0 mm 선형 감소 (주기 그라디언트).
  - `A_profile(z)`: 0.5 → 0.0 (거칠기 진폭).
  - `phase_z`: Z에 대해 `d_phase = (2π/L(z)) * dz` 적분한 위상.
- **슬라이스별 수식** (단위: m):
  - `k_xy = 2π / (L/1000)`
  - `base_val = sin(k_xy*X)*cos(k_xy*Y) + sin(k_xy*Y)*cos(pz) + sin(pz)*cos(k_xy*X)`  
    (Z는 위상 `pz = phase_z[k]`로만 들어감.)
  - 거칠기: `base_val += A * sin(4*k_xy*X)*sin(4*k_xy*Y)*sin(4*pz)` (A>0.001일 때).
- **Solid 판정**: `|val| < t_level(z)` → Solid.  
  `t_levels = 1.3 * sin((t_wall_mm*π) / (2*L_profile))` (Z별로 다름).
- **마스크**: 외벽 2 voxel 두께로 벽=1, 버퍼 5 voxel씩 유체=0.

즉, **단일 주기·단일 t_level이 아니라**, Z에 따라 **L(z), A(z), t_level(z), phase_z**가 바뀌는 **그라디언트/변수 자이로이드**입니다.

### 3.2 Taichi init_structure / gyroid_taichi_formula (우리 쪽)

- **도메인**: dx=0.2 mm, 25.4×25.4×110 mm, Z 버퍼 5~105 mm만 메인.
- **수식** (mm 단위, **주기 고정**):
  - `k_g = 2*π / a` (a: 주기 mm, 예: 5).
  - `val = sin(k_g*x)*cos(k_g*y) + sin(k_g*y)*cos(k_g*z) + sin(k_g*z)*cos(k_g*x)`  
    → **x, y, z 모두 물리 좌표**로 들어가는 표준 자이로이드.
- **Solid 판정**: `val > t_level` → Solid (단일 상수 t_level, 예: 0.768).
- **외벽**: `x<1 or x>24.4 or y<1 or y>24.4` → Solid (Taichi). STL은 `empty_duct_v32.stl`로 별도.

### 3.3 요약 비교

| 항목 | Gradient_Smooth_Fine (generate_gyroid_smooth) | Taichi / gyroid_taichi_formula |
|------|----------------------------------------------|---------------------------------|
| 주기 | Z에 따라 L(z)=14→10 mm 변함 | 고정 `a` (예: 5 mm), `k_g=2π/a` |
| Z 의존 | phase_z 적분, L(z), A(z), t_level(z) | z가 수식에 그대로 들어감 (표준 자이로이드) |
| Solid 조건 | `\|val\| < t_level(z)` | `val > t_level` (단일 상수) |
| 도메인 길이 | 100 mm (+ 마스크 버퍼 5 voxel) | 110 mm (메인 5~105, 버퍼 포함) |
| 외벽 구현 | .npy에는 2 voxel 벽 포함, **STL은 casing 기하로만** | STL은 자이로이드만, 외벽은 empty_duct_v32.stl |

**결론**:  
- **형상 생성 방식(외벽 + 자이로이드)** 은 Gradient_Smooth_Fine이 “**기하 casing + voxel 자이로이드 메쉬 append**”로 외벽을 확실히 막는 점에서 우리가 따르기 좋은 참고입니다.  
- **자이로이드 수식 자체는 일치하지 않습니다.** Gradient_Smooth는 Z 그라디언트·위상 적분·거칠기 항이 있는 **변수 자이로이드**이고, Taichi/gyroid_taichi_formula는 **고정 주기·단일 t_level의 표준 자이로이드**입니다.  
- Taichi와 완전히 같은 형상을 쓰려면, 지금처럼 **표준 수식 + empty_duct_v32.stl(외벽) + 자이로이드만 STL → voxel union 또는 메쉬 append** 방식이 맞고, Gradient_Smooth_Fine은 “외벽 구현 방식”만 참고하고, 내부 수식은 우리 수식과 다르다는 점만 맞추면 됩니다.

---

## 4. 우리 쪽에 적용할 수 있는 개선 (선택)

- **STL 한 파일로 합치기** (Gradient_Smooth_Fine처럼):  
  - 외벽: OpenSCAD로 만든 `empty_duct_v32.stl`을 PyVista 등으로 로드.  
  - 자이로이드: `gyroid_taichi_formula.py`로 만든 **자이로이드만** STL 로드.  
  - `merged = casing_mesh + gyroid_mesh` 로 append 후 한 STL로 저장.  
  → 외벽은 항상 기하 덕트만 쓰므로, Gradient_Smooth_Fine과 동일하게 “외벽 구멍 없음”을 보장할 수 있음.

이 문서는 `Gradient_Smooth_Fine.stl` 생성 코드 조사 및 Taichi 수식과의 비교 결과를 정리한 것입니다.

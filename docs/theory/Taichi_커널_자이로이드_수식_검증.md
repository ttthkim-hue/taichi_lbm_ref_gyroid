# Taichi 커널 자이로이드 수식 구현·검증

## 1. 현재 구조 (아카이브 taichi_lbm_solver_v3.py)

- **형상**: `--mask` 로 **.npy 마스크 파일**을 불러와 `ti.field`에 넣어 사용.
- **수식 커널 없음**: `--mask` 미지정 시 단순 직관(32×32×128, XY 가장자리만 벽) fallback만 있음.
- 따라서 **자이로이드 형상을 코드로 쓰려면** (1) STL→voxel .npy를 쓰거나, (2) 아래와 같은 **init_structure() 수식 커널**을 추가해 마스크를 채워야 함.

---

## 2. STL/수식과 일치하는 Taichi 커널 (제안)

아래는 `gyroid_taichi_formula.py` 및 `empty_duct_v32` STL과 **동일한 규칙**으로 마스크를 채우는 커널이다.  
격자: **dx = 0.2 mm**, **127×127×550** (25.4×25.4×110 mm).  
셀 중심 좌표: `x_mm = (i+0.5)*dx`, `y_mm = (j+0.5)*dx`, `z_mm = (k+0.5)*dx` (mm).

```python
# 상수 (V3.2 공통)
# dx = 0.2  # mm
# a = 5.0   # 주기 [mm]
# t_level = 0.768
# k_g = 2*π/a

@ti.kernel
def init_structure():
    for i, j, k in mask_field:
        # 1. 물리 좌표 (mm). 셀 중심으로 하면 voxel STL과 일치.
        x = (ti.cast(i, ti.f64) + 0.5) * dx
        y = (ti.cast(j, ti.f64) + 0.5) * dx
        z = (ti.cast(k, ti.f64) + 0.5) * dx

        # 2. 외벽 판별 (25.4 mm 정사각형, 내부 23.4 mm → 벽 1 mm)
        is_wall = (x < 1.0 or x > 24.4 or y < 1.0 or y > 24.4)

        if is_wall:
            mask_field[i, j, k] = 1   # Solid
        elif z < 5.0 or z > 105.0:
            mask_field[i, j, k] = 0   # Fluid (입출구 버퍼)
        else:
            # 3. 자이로이드 수식 (Main 5~105 mm). k_g = 2*pi/a
            val = ti.sin(k_g * x) * ti.cos(k_g * y) + \
                  ti.sin(k_g * y) * ti.cos(k_g * z) + \
                  ti.sin(k_g * z) * ti.cos(k_g * x)
            if val > t_level:
                mask_field[i, j, k] = 1   # Solid
            else:
                mask_field[i, j, k] = 0   # Fluid
```

- **좌표**: `(i+0.5)*dx` 사용 시 `stl_to_voxel_v32.py`의 셀 중심 좌표와 동일.
- **경계**: `x,y ∈ [1, 24.4]`, `z ∈ [5, 105]` 메인, 그 외 버퍼/외벽 → STL·문서와 일치.

---

## 3. 검증 방법

### A. 수식 마스크 .npy 생성 후 솔버에 넣기

- `scripts/init_gyroid_mask_v32.py` 로 **동일 수식**을 NumPy로 적용해 `gyroid_duct_v32_formula.npy` 생성.
  ```bash
  python3 scripts/init_gyroid_mask_v32.py -o geometry_openscad/gyroid_duct_v32_formula.npy
  ```
- 아카이브 솔버에서: `taichi_lbm_solver_v3.py --mask geometry_openscad/gyroid_duct_v32_formula.npy --dx 0.0002 ...` 로 실행해 LBM이 정상 동작하는지 확인. (dx는 m 단위이면 0.0002)

### B. STL voxel 마스크와 수식 마스크 비교

- `stl_to_voxel_v32.py` 로 `empty_duct_v32.stl` + `gyroid_taichi_formula.stl` → `gyroid_duct_v32_stl.npy` 생성.
- `init_gyroid_mask_v32.py` 로 `gyroid_duct_v32_formula.npy` 생성.
- 두 .npy를 비교: `np.allclose(m1, m2)` 또는 `(m1 != m2).sum()` 으로 불일치 셀 수 확인.  
  → 일치하면 “Taichi 커널에서 코드로 구현해도 STL 기반 voxel과 동일 형상”으로 검증됨.

### C. Taichi 커널에서 직접 init_structure() 사용

- 솔버에 `--mask` 대신 `--gyroid_formula` 옵션을 두고, 위 `init_structure()` 커널로 `mask_field`를 채운 뒤 기존 LBM 루프 사용.
- 이때 NX, NY, NZ, dx, k_g, t_level을 V3.2와 동일하게 두면, (B)와 같은 형상이 Taichi 내부에서 코드로만 생성됨.

---

## 4. 요약

| 항목 | STL / voxel | Taichi 수식 커널 (제안) |
|------|-------------|--------------------------|
| 외벽 | empty_duct 1 mm 막힌 벽 | x&lt;1 or x&gt;24.4 or y&lt;1 or y&gt;24.4 → 1 |
| 버퍼 | z&lt;5, z&gt;105 유체 | 동일 → 0 |
| 자이로이드 | val &gt; t_level → Solid | val = sin(k_g*x)cos(k_g*y)+... , val&gt;t_level → 1 |
| 좌표 | 셀 중심 (i+0.5)*dx | 동일 권장 |
| 격자 | 127×127×550, dx=0.2 mm | 동일 |

위 커널을 Taichi 솔버에 넣고, (A)(B)(C) 순으로 검증하면 “STL은 OK이고, 나중에 Taichi 커널에서 코드로 구현해도 동일하게 잘 된다”를 확인할 수 있다.

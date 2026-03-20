# 지오메트리 (최신본) — OpenSCAD + Taichi 수식 자이로이드

LBM 검증용 **빈 덕트**, **Reference 6×6**, **자이로이드** 형상.  
자이로이드는 **Taichi `init_structure()`와 동일한 수식**으로 STL을 생성해 검증 후, 향후에는 매싱 없이 Taichi에 수식만 넣을 예정.

## 공통 치수 (V3.2)

| 항목 | 값 |
|------|-----|
| 외부 단면 | 25.4×25.4 mm |
| 외벽 두께 | 1 mm → 내부 23.4×23.4 mm |
| 전체 길이 Z | 110 mm |
| Inlet buffer | Z = 0~5 mm |
| Main (Test Section) | Z = 5~105 mm (100 mm) |
| Outlet buffer | Z = 105~110 mm |

## 파일 구성

| 파일 | 설명 |
|------|------|
| `empty_duct_v32.scad` / `.stl` | 빈 덕트 (25.4 외부 − 23.4 내부, 110 mm) |
| `reference_6x6_v32.scad` / `.stl` | 6×6 채널 (Main 구간만 격자벽, 내벽 1 mm) |
| `gyroid_taichi_formula.py` / `.stl` | Taichi 수식 **자이로이드만** (외벽 없음). 외벽은 반드시 `empty_duct_v32.stl` 사용. |

## 사용법

### 1. 빈 덕트 (OpenSCAD)

```bash
openscad -o empty_duct_v32.stl empty_duct_v32.scad
```

### 2. Reference 6×6 (OpenSCAD)

```bash
openscad -o reference_6x6_v32.stl reference_6x6_v32.scad
```

### 3. 자이로이드 (Taichi 수식, Python) — 자이로이드만, 외벽 없음

**외벽 1.0 mm 솔리드(막힌 벽)** 는 OpenSCAD `empty_duct_v32.stl` 로만 적용.  
본 스크립트는 **Main 구간(5~105 mm) 내부 23.4×23.4** 에서 `val > t_level` 인 자이로이드만 출력하여, 외벽에 구멍이 생기지 않음.

**수식** (Taichi `init_structure()` 와 동일):  
`val = sin(k_g*x)*cos(k_g*y) + sin(k_g*y)*cos(k_g*z) + sin(k_g*z)*cos(k_g*x)`, `k_g = 2*pi/a`.

```bash
python3 gyroid_taichi_formula.py --a 5 --t_level 0.768 --res 60 --out gyroid_taichi_formula.stl
```

- `--a`: 주기 [mm]. 기본 5.
- `--t_level`: val > t_level → Solid. 기본 0.768.
- `--res`: 해상도. 60~80 권장.

**Taichi 코드와의 일치**: `init_structure()` 에서 `is_wall` → Solid, 버퍼 → Fluid, 메인에서 `val > t_level` → Solid. STL은 외벽을 `empty_duct_v32.stl`, 자이로이드를 본 STL로 두고 voxel union 하면 동일 형상.

## STL → Voxel (LBM 마스크)

프로젝트 루트의 `scripts/stl_to_voxel_v32.py` 사용. 자이로이드 덕트 전체(외벽+자이로이드)는 `empty_duct_v32.stl`과 `gyroid_taichi_formula.stl`을 함께 넘겨 voxel 공간에서 union.

```bash
python3 scripts/stl_to_voxel_v32.py geometry_openscad/empty_duct_v32.stl geometry_openscad/gyroid_taichi_formula.stl -o geometry_openscad/gyroid_duct_mask.npy
```

(trimesh 필요 시 `.venv_v32/bin/python` 사용)

# Gyroid Generator — 종합분석보고서

## 1. 프로젝트 개요

Gyroid TPMS(Triply Periodic Minimal Surface) 촉매 지지체의 STL/STEP 형상을
파라미터 조절로 생성하는 Windows GUI 프로그램.

- 수식 기반 implicit surface → marching cubes → STL (1차 출력물)
- STL → OCP sewing → STEP (2차 변환, tessellated B-Rep)
- PyInstaller onedir 모드로 빌드, GitHub Actions CI 자동화

## 2. 핵심 수식

```
phi(x,y,z) = sin(kx)cos(ky) + sin(ky)cos(kz) + sin(kz)cos(kx)
k = 2*pi / a

Solid: phi > -t    (네트워크 타입)
Fluid: phi <= -t
```

| 파라미터 | 의미 | 범위 | 기본값 |
|---------|------|------|--------|
| a | 단위셀 크기 [mm] | 4.0 ~ 8.0 | 5.0 |
| t | 레벨셋 오프셋 | 0.02 ~ 0.10 | 0.10 |
| res (STL) | 메시 해상도 | 30 ~ 120 | 60 |
| res (STEP) | STEP 전용 해상도 | 3 ~ 15 | 8 |

## 3. 벽두께 분석 (검증 완료)

### 3.1 측정 방법론 비교

| 방법 | 원리 | 결과 | 평가 |
|------|------|------|------|
| Erosion | `dt > r`이 사라지는 r 탐색 | 2.56mm (a=5,t=0.3) | **최대 벽두께 측정 — 틀림** |
| 2D Medial Axis | 슬라이스별 골격 | 0.08mm (일정) | **voxel 해상도 반환 — 틀림** |
| **Local Max** | **EDT의 골격 local maxima 최소값** | **0.24mm (a=5,t=0.3)** | **정확 — 채택** |

### 3.2 Erosion 방식이 틀린 이유

```
dt = distance_transform_edt(solid)   # 각 solid voxel → 최근접 fluid 거리

# Erosion: dt > r 인 voxel이 하나도 없으면 break
# → 모든 solid voxel의 distance가 r 이하 → MAX inscribed sphere
# → 가장 두꺼운 벽의 반두께를 반환

# 올바른 방법: local maxima of dt → medial axis 위의 최소값
# → 가장 얇은 벽의 반두께를 반환
```

### 3.3 정확한 벽두께 테이블 (Local Max, 2x2x2 주기 타일링)

```
         a=3    a=4    a=5    a=6    a=8
t=0.00   1.32   1.76   2.20   2.63   3.51   ← 50% 체적분율
t=0.02   1.32   1.76   2.20   2.63   3.51
t=0.06   0.78*  1.04   1.30   1.56   2.08
t=0.10   1.35   1.80   2.25   2.70   3.60   ← 기본값 (안전)
t=0.20   0.89*  1.19   1.49   1.78   2.38   ← 경계 영역
t=0.25   0.10*  0.14*  0.17*  0.21*  0.28*  ← 위상전이
t=0.30   0.15*  0.20*  0.24*  0.29*  0.39*  ← 프린팅 불가
                                              (* = < 1mm)
```

### 3.4 위상전이 현상

t ≈ 0.20~0.25에서 유체 채널이 닫히면서:
- 고립된 유체 포켓 생성
- 포켓 주위에 0.1~0.4mm 얇은 막(membrane) 형성
- 3D 프린팅 시 파손 원인

## 4. 외벽 결합 문제 (발견 및 수정)

### 4.1 문제: concatenate ≠ boolean union

```python
# 이전 (문제):
combined = trimesh.util.concatenate([gyroid_mesh, duct_wall])
# → 두 메시를 단순 적층. 교차/겹침 검증 없음.
# → 자이로이드 경계(x=1.0, x=24.4)와 덕트 내벽이 정확히 접촉
# → 비매니폴드 표면, 얇은 슬라이버(sliver) 아티팩트

# 수정 (정상):
combined = duct_wall.union(gyroid_mesh, engine="manifold")
# → Manifold 엔진으로 boolean union
# → 교차면 자동 처리, 매니폴드 메시 보장
```

### 4.2 자이로이드-덕트 경계 조건

```
덕트 외벽: 25.4 x 25.4 x 110 mm
덕트 내벽: 23.4 x 23.4 mm (벽두께 1.0mm)
자이로이드 도메인: x ∈ [1.0, 24.4], y ∈ [1.0, 24.4]
→ 자이로이드와 덕트 내벽이 정확히 같은 경계를 공유
→ concatenate 시 경계에서 이중 표면(double surface) 발생
→ union 시 자동으로 merge/정리
```

## 5. STEP 생성 아키텍처

### 5.1 왜 STL → STEP인가 (역순이 아닌 이유)

자이로이드는 **초월함수 implicit surface**:
```
phi = sin(kx)cos(ky) + sin(ky)cos(kz) + sin(kz)cos(kx) = -t
```
이것은 NURBS 곡면으로 정확하게 표현이 불가능.
→ marching cubes → STL이 1차 출력물
→ STL → STEP는 삼각형을 STEP 포맷으로 감싼 것 (tessellated B-Rep)
→ ANSYS에서 STL 직접 import가 더 효율적

### 5.2 STEP 변환 파이프라인

```
GUI (gyroid_gui.py)              step_converter.exe (별도 프로세스)

저해상도 자이로이드 생성    →    OCP import
                                 StlAPI_Reader로 로드
                                 BRepBuilderAPI_Sewing (O(n^2))
                                 Shell → Solid 변환
                                 STEPControl_Writer (AP214)
GUI에서 실시간 로그 읽기    ←    stdout 출력 (영문)
```

분리 이유: OCP/OCCT C++ DLL이 Python GIL을 점유하여 GUI가 멈추는 문제 해결.

### 5.3 STEP 소요시간 (Windows, a=5, t=0.10)

| STEP 해상도 | 면 수 | Sewing 시간 | 파일 크기 |
|-------------|-------|------------|----------|
| 3 | ~10K | ~1분 | ~30 MB |
| 5 | ~100K | ~8분 | ~240 MB |
| 8 | ~300K | 20분+ | ~700 MB |

## 6. 십자 단면 STL

XY 중심축으로 메시를 4분할, 각 사분면을 12.5mm씩 이동(gap=25mm).
trimesh.slice_plane(cap=True)로 절단면 캡 처리.

```
  Q2 |     | Q1        각 사분면:
  ---+     +---        cx = (xmin+xmax)/2 = 12.7mm
     |25mm |           cy = (ymin+ymax)/2 = 12.7mm
  ---+     +---        gap/2 = 12.5mm 이동
  Q3 |     | Q4
```

## 7. 파일 구조

```
GyroidGenerator_onedir/          (배포 패키지)
├── GyroidGenerator.exe          (16MB, 메인 GUI)
├── step_converter.exe           (16MB, OCP 전용)
├── _internal/                   (520MB, Python + DLL)
└── 사용법.txt

소스코드:
├── gyroid_gui.py                (메인 GUI + 형상 생성)
├── step_converter.py            (OCP STEP 변환 — 별도 프로세스)
├── GyroidGenerator.spec         (PyInstaller onedir 설정)
└── pyi_rth_gyroid_ocp.py        (OCP DLL 런타임 훅)
```

## 8. CI/CD (GitHub Actions)

```
워크플로: build-gyroid-generator-windows.yml
트리거: push to main (해당 폴더 변경 시)

Job 1: verify-python-syntax (Ubuntu)
  → py_compile gyroid_gui.py

Job 2: pyinstaller-windows (Windows)
  → pip install numpy scipy scikit-image trimesh manifold3d
    shapely rtree cadquery pyinstaller
  → STEP 파이프라인 검증 (20x20x20 그리드)
  → PyInstaller --noconfirm GyroidGenerator.spec
  → Upload artifact: GyroidGenerator-windows
```

## 9. 벽두께 계산 코드 (최종 — Local Max 방식)

```python
@staticmethod
def _calc_min_wall(a: float, t: float, grid_n: int = 100) -> float:
    from scipy.ndimage import distance_transform_edt, maximum_filter

    voxel = a / grid_n
    n2 = grid_n * 2
    lin = np.linspace(0, 2 * a, n2, endpoint=False) + voxel / 2
    x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
    k = 2.0 * np.pi / a
    phi = sin(kx)cos(ky) + sin(ky)cos(kz) + sin(kz)cos(kx)
    solid = phi > -t

    dt = distance_transform_edt(solid) * voxel  # mm 단위

    # 경계 효과 제거 (2x2x2 타일 중앙만 사용)
    m = grid_n // 4
    dt_c = dt[m:-m, m:-m, m:-m]
    solid_c = solid[m:-m, m:-m, m:-m]

    # 골격(medial axis) = distance field의 local maxima
    lm = maximum_filter(dt_c, size=3)
    ridge = (dt_c == lm) & solid_c & (dt_c > voxel * 1.5)

    # ridge 위 최소값 * 2 = 가장 얇은 벽의 전체 두께
    return float(dt_c[ridge].min()) * 2
```

## 10. 외벽 결합 코드 (수정 후 — Boolean Union)

```python
if include_duct:
    outer_box = trimesh.creation.box(extents=[25.4, 25.4, 110])
    outer_box.apply_translation([12.7, 12.7, 55])
    inner_box = trimesh.creation.box(extents=[23.4, 23.4, 112])
    inner_box.apply_translation([12.7, 12.7, 55])
    duct_wall = outer_box.difference(inner_box, engine="manifold")

    # boolean union (manifold 엔진)
    combined = duct_wall.union(gyroid_mesh, engine="manifold")
    # fallback: concatenate (union 실패 시)
```

## 11. 주요 발견사항 요약

| # | 항목 | 문제 | 심각도 | 조치 |
|---|------|------|--------|------|
| 1 | 벽두께 계산 | erosion = 최대벽두께 (반대값) | Critical | local max로 교체 |
| 2 | 외벽 결합 | concatenate = 비매니폴드 | High | boolean union으로 교체 |
| 3 | t 기본값 | 0.30 → 얇은 막 생성 | High | 0.10으로 변경 |
| 4 | 단면 gap | 5mm → 내부 안 보임 | Medium | 25mm로 변경 |
| 5 | STEP 변환 | GUI 멈춤 | Medium | subprocess 분리 완료 |
| 6 | 콘솔 인코딩 | cp949 한글 깨짐 | Low | 영문 전환 완료 |

## 12. 향후 과제

1. NURBS fitting 연구 — 자이로이드를 진짜 B-Rep STEP으로 만들 수 있는지 검토
2. ANSYS SpaceClaim "Facets to BRep" 자동화 연동
3. Diamond TPMS 등 다른 격자 타입 추가 (gyroid_xlb에 구현 완료)
4. Bayesian Optimization 연동 — a, t 최적 조합 자동 탐색

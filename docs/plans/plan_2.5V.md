# 작업지시서 — plan_2.4V-fix (Gyroid 유동 진단 + VTI 수집)

**작성일:** 2026-03-19  
**문제:** Gyroid 3-g에서 u_mean ≈ 0, K 음수. 유동이 안 흐름.

---

## 0. 실행 전 필수: 패키지 설치 확인

```bash
pip install pyevtk pyvista --break-system-packages
# 이미 설치돼 있으면 무시됨
# pyevtk: VTR 저장용
# pyvista: 시각화용
```

---

## 1. 진단 Phase 1: 코드 확인 (시뮬 불필요, 5분)

### 1.1 Gyroid 마스크 Z방향 연결성 확인

`scripts/diag_gyroid_connectivity.py` 신규 작성:

```python
"""
Gyroid 마스크 생성 후 Z 관통 경로 수 확인.
시뮬 불필요 — 마스크만 생성하여 분석.
"""
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMCore

ti.init(arch=ti.cuda)

NX, NY, NZ = 131, 131, 550
DX = 0.2e-3
A_MM, T = 5.0, 0.3
WALL = 5

core = TaichiLBMCore(NX, NY, NZ, tau=0.595)
core.set_geometry_gyroid_kernel(A_MM, T, WALL)
solid = core.solid.to_numpy()  # (NX, NY, NZ), 0=fluid, 1=solid

# ── 진단 1: Z 관통 경로 ──
fluid_all_z = np.all(solid == 0, axis=2)
n_through = int(np.sum(fluid_all_z))
print(f"[진단1] Z 관통 유체 셀 수: {n_through}")
print(f"  → {'❌ Z 방향 막힘 (Sheet 분리)' if n_through == 0 else '✅ Z 관통 경로 있음'}")

# ── 진단 2: 슬라이스별 유체 비율 ──
print("\n[진단2] 슬라이스별 유체 비율:")
for z in [0, 5, 50, 100, 275, 450, 500, 545, 549]:
    ratio = np.mean(solid[:,:,z] == 0)
    print(f"  z={z:3d}: fluid={ratio:.4f}")

# ── 진단 3: 전체 공극률 ──
eps = np.mean(solid == 0)
print(f"\n[진단3] 전체 공극률 ε = {eps:.4f}")

# ── 진단 4: XY 중앙 단면 solid 패턴 ──
mid_z = NZ // 2
mid_y = NY // 2
print(f"\n[진단4] solid 패턴 (z={mid_z}):")
print(f"  유체 셀 수: {np.sum(solid[:,:,mid_z]==0)} / {NX*NY}")

print(f"\n[진단4] solid 패턴 XZ (y={mid_y}):")
print(f"  유체 셀 수: {np.sum(solid[:,mid_y,:]==0)} / {NX*NZ}")

# ── 진단 5: 외벽 내부만 Z 관통 확인 ──
interior = solid[WALL:-WALL, WALL:-WALL, :]  # 외벽 제외
fluid_interior_z = np.all(interior == 0, axis=2)
n_interior = int(np.sum(fluid_interior_z))
print(f"\n[진단5] 외벽 제외 내부 Z 관통: {n_interior}")
```

**실행:**

```bash
python scripts/diag_gyroid_connectivity.py 2>&1 | tee logs/diag_connectivity.txt
```

**판정:**
- `n_through = 0` → **원인 A 확정** (Sheet 분리). §3 해결로 진행.
- `n_through > 0` → §1.2, §1.3 확인 후 VTI로 상세 진단.

### 1.2 체적력 방향 확인

`solver/taichi_lbm_core.py`에서 검색:

```
확인: Guo forcing에서 체적력이 Z 방향(인덱스 2)에 +g_lbm으로 들어가는지
확인: D3Q19 velocity set에서 Z 양의 방향이 k+1인지 k-1인지
확인: L2-B(6×6 주기BC)에서 u_channel이 양수(0.476)였으므로, 같은 코드 경로면 방향은 맞음
```

### 1.3 get_flux_z 부호 확인

```
확인: get_flux_z(z)가 Σ(ρ[i,j,z] × vel[i,j,z,2])인지 Σ(vel[i,j,z,2])인지
확인: L2-B 로그에서 Q_phys가 양수였는지
```

---

## 2. 진단 Phase 2: VTI 수집 + 시각화

**§1.1에서 원인이 확정되더라도 VTI는 반드시 수집합니다.** 논문 그래프 및 향후 디버깅 자료로 사용.

### 2.1 VTI 수집 스크립트

`scripts/save_vti_gyroid_diag.py` 신규 작성:

```python
"""
Gyroid 진단용 VTI/VTR 저장.
주기BC + 체적력 g=5e-6, 5000스텝 실행 후 유동장 저장.
"""
import numpy as np
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMCore, TaichiLBMWrapper

# ── 설정 ──
NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
DX = DX_MM * 1e-3
NU_PHYS = 3.52e-5
RHO_PHYS = 0.746
TAU = 0.595
A_MM, T_PARAM = 5.0, 0.3
WALL_VOXELS = 5
G_LBM = 5e-6
MAX_STEPS = 5000
SAVE_INTERVAL = 1000  # 매 1000스텝 VTR 저장

ti.init(arch=ti.cuda)

# ── 솔버 생성 ──
wrapper = TaichiLBMWrapper(
    NX, NY, NZ, DX, NU_PHYS, RHO_PHYS,
    u_in_phys=0.0,  # 주기BC에서는 사용 안 함
    tau=TAU,
    mode="periodic_body_force"
)
wrapper.set_geometry_gyroid_kernel(A_MM, T_PARAM, WALL_VOXELS)
wrapper.set_body_force_z(G_LBM)

# ── 실행 + VTR 저장 ──
def save_vtr(step_label):
    """현재 유동장을 VTR로 저장"""
    from pyevtk.hl import gridToVTK
    
    rho_np = wrapper.core.rho.to_numpy()
    vel_np = wrapper.core.vel.to_numpy()  # (NX,NY,NZ,3)
    solid_np = wrapper.core.solid.to_numpy()
    
    vz = vel_np[:,:,:,2]
    
    # 격자 좌표 (mm 단위)
    x = np.arange(0, NX+1, dtype=np.float64) * DX_MM
    y = np.arange(0, NY+1, dtype=np.float64) * DX_MM
    z = np.arange(0, NZ+1, dtype=np.float64) * DX_MM
    
    path = f"results/gyroid_diag_step{step_label}"
    gridToVTK(
        path, x, y, z,
        cellData={
            "rho": np.ascontiguousarray(rho_np, dtype=np.float64),
            "vz": np.ascontiguousarray(vz, dtype=np.float64),
            "solid": np.ascontiguousarray(solid_np.astype(np.float64)),
        }
    )
    print(f"  VTR 저장: {path}.vtr")

# 초기 상태 저장
save_vtr("0000")

# 시뮬 실행
for step in range(1, MAX_STEPS+1):
    wrapper.core.step()
    
    if step % SAVE_INTERVAL == 0:
        # 유량 측정
        z_mid = NZ // 2
        flux = wrapper.core.get_flux_z(z_mid)
        rho_mean = wrapper.core.get_rho_mean_fluid()
        
        print(f"  step {step}: flux_z(mid)={flux:.6f}, rho_mean={rho_mean:.6f}")
        save_vtr(f"{step:04d}")

# 최종 저장
save_vtr("final")
print("\n[완료] VTR 파일 저장 위치: results/gyroid_diag_*.vtr")
```

> ⚠️ 위 코드는 의도 전달용. wrapper/core의 실제 메서드명에 맞춰 수정할 것.
> 특히 `wrapper.core.vel`, `wrapper.core.rho`, `wrapper.core.step()` 등의 이름을 확인.

### 2.2 실행

```bash
python scripts/save_vti_gyroid_diag.py 2>&1 | tee logs/vti_gyroid_diag.txt
```

**예상 시간: ~15분** (5000스텝 + VTR 저장 6회)

### 2.3 VTR 파일 목록 (예상)

```
results/
  gyroid_diag_step0000.vtr    # 초기 (유동 전)
  gyroid_diag_step1000.vtr
  gyroid_diag_step2000.vtr
  gyroid_diag_step3000.vtr
  gyroid_diag_step4000.vtr
  gyroid_diag_step5000.vtr
  gyroid_diag_final.vtr       # 최종
```

### 2.4 pyvista 확인 항목 (자동 PNG 생성 + 필요 시 ParaView 추가 확인)

**§2.5 스크립트가 자동으로 PNG를 생성합니다. 추가 확인이 필요하면 VTR을 ParaView에서 열어도 됩니다.**

| # | 확인 항목 | 자동 생성 PNG | 기대 결과 | 이상 시 원인 |
|---|-----------|--------------|-----------|-------------|
| 1 | **solid XY (z=275)** | `gyroid_solid_xy_z275.png` | Gyroid 패턴, 열린 유로 | 전부 solid → 마스크 오류 |
| 2 | **solid XZ (y=65)** | `gyroid_solid_xz_y65.png` | Z 관통 유로 보임 | 관통 없음 → Sheet 분리 |
| 3 | **3D fluid** | `gyroid_3d_fluid.png` | 연결된 유체 영역 | 분리된 덩어리 → 관통 없음 |
| 4 | **vz XY (z=275)** | `gyroid_vz_xy_z275.png` (VTR 필요) | 유체에서 양의 vz | 0 또는 음수 → 방향 문제 |

### 2.5 시각화 스크립트 (pyvista)

> **시각화는 pyvista로 통일한다.** `pip install pyvista --break-system-packages`

`scripts/visualize_gyroid_diag.py` 신규 작성:

```python
"""
Gyroid 마스크 + 유동장 pyvista 시각화.
VTR 파일이 있으면 VTR에서 로드, 없으면 마스크만 생성하여 시각화.
"""
import numpy as np
import pyvista as pv
import taichi as ti
from solver.taichi_lbm_core import TaichiLBMCore

pv.OFF_SCREEN = True  # 헤드리스 환경용

ti.init(arch=ti.cuda)

NX, NY, NZ = 131, 131, 550
DX_MM = 0.2
core = TaichiLBMCore(NX, NY, NZ, tau=0.595)
core.set_geometry_gyroid_kernel(5.0, 0.3, 5)
solid = core.solid.to_numpy()

# ── UniformGrid 생성 ──
grid = pv.ImageData(dimensions=(NX+1, NY+1, NZ+1), spacing=(DX_MM, DX_MM, DX_MM))
grid.cell_data["solid"] = solid.flatten(order="F")

# ── 1. XY 단면 (z=275) — solid 패턴 ──
slice_xy = grid.slice(normal="z", origin=(0, 0, 275*DX_MM))
pl = pv.Plotter(off_screen=True)
pl.add_mesh(slice_xy, scalars="solid", cmap="gray", show_edges=False)
pl.add_title("solid XY (z=275)")
pl.camera_position = "xy"
pl.screenshot("results/gyroid_solid_xy_z275.png", window_size=[1200, 1200])
pl.close()

# ── 2. XZ 단면 (y=65) — Z 관통 확인 ──
slice_xz = grid.slice(normal="y", origin=(0, 65*DX_MM, 0))
pl = pv.Plotter(off_screen=True)
pl.add_mesh(slice_xz, scalars="solid", cmap="gray", show_edges=False)
pl.add_title("solid XZ (y=65) — Z 관통 확인")
pl.camera_position = "xz"
pl.screenshot("results/gyroid_solid_xz_y65.png", window_size=[1600, 400])
pl.close()

# ── 3. 3D isosurface (solid 경계면) ──
fluid = grid.threshold(value=0.5, scalars="solid", invert=True)  # solid=0 추출
pl = pv.Plotter(off_screen=True)
pl.add_mesh(fluid, color="steelblue", opacity=0.3)
pl.add_title("Gyroid fluid region (3D)")
pl.camera_position = "iso"
pl.screenshot("results/gyroid_3d_fluid.png", window_size=[1200, 1200])
pl.close()

print("저장 완료:")
print("  results/gyroid_solid_xy_z275.png")
print("  results/gyroid_solid_xz_y65.png")
print("  results/gyroid_3d_fluid.png")
```

**VTR이 있는 경우 유동장 시각화 추가:**

```python
# VTR 로드 후 vz 시각화
if os.path.exists("results/gyroid_diag_step5000.vtr"):
    mesh = pv.read("results/gyroid_diag_step5000.vtr")
    
    # vz XY 단면
    sl = mesh.slice(normal="z", origin=(0, 0, 275*DX_MM))
    pl = pv.Plotter(off_screen=True)
    pl.add_mesh(sl, scalars="vz", cmap="coolwarm", show_edges=False)
    pl.add_title("vz XY (z=275, step 5000)")
    pl.camera_position = "xy"
    pl.screenshot("results/gyroid_vz_xy_z275.png", window_size=[1200, 1200])
    pl.close()
```

**실행:**

```bash
pip install pyvista --break-system-packages  # 최초 1회
python scripts/visualize_gyroid_diag.py
```

**PNG 3장(+ VTR 있으면 4장)으로 Z 관통 여부와 유동 패턴이 즉시 보입니다.**

---

## 3. 예상 원인별 해결

### 원인 A: Sheet Gyroid가 Z 방향으로 막혀 있음 (가장 유력)

Sheet Gyroid `|φ| < t`는 벽의 양쪽에 **분리된 두 채널 네트워크** 생성. Z 관통 보장 안 됨.

| 타입 | 조건 | 채널 | Z 관통 |
|------|------|------|--------|
| Sheet | \|φ\| < t | 분리된 2개 (φ>t, φ<-t) | ❌ 보장 안 됨 |
| Network+ | φ < -t (유체) | 단일 연결 | ✅ 보장 |

**해결 (권장: Network 타입으로 변경):**

```python
# 기존 (Sheet):
# solid = 1 if |phi| < t else 0

# 수정 (Network):
# solid = 1 if phi > -t else 0   (φ < -t 영역이 유체)
# 또는
# solid = 1 if phi > t else 0    (φ < t 영역이 유체, 더 넓음)
```

> ⚠️ Network 타입의 ε는 Sheet와 다름. t=0.3에서:
> - Sheet: ε ≈ 0.80
> - Network+: ε ≈ 0.60 (대략)
> BO 설계 변수 범위(ε ∈ [0.35, 0.65])에 더 부합할 수 있음.

### 원인 B: 체적력 방향이 -Z

**해결:** g_lbm 부호 반전.

### 원인 C: get_flux_z 부호/정의 오류

**해결:** vz 부호 확인 후 수정.

---

## 4. 실행 순서

```
1. §1.1 연결성 진단 스크립트 실행 — 2분
   → n_through 값으로 원인 A 즉시 판별

2. §2.5 pyvista 시각화 — 2분  
   → solid 단면 + 3D PNG로 시각 확인

3. §2.1~2.2 VTI 수집 (5000스텝) — 15분
   → VTR 파일 7개 저장 + vz 시각화 PNG 추가

4. 원인 확정 → §3 수정

5. Gyroid 3-g 재실행 (5k 스텝 우선) — 15분
   → 5k 결과에서 K 수렴 추이 확인
   → K가 안정되었으면 그대로 판정
   → 아직 변하고 있으면 20k까지 연장

6. GCI 3-level — 80분 (3-g PASS 후)
```

**1~3은 병렬 불가 (같은 GPU). 순차 실행.**
**총 예상: 진단 20분 + 수정 10분 + 3-g 15분(~60분) + GCI 80분 = ~2~3시간**

---

## 5. Sheet vs Network — 논문 관점

**SCR 촉매에서 Sheet와 Network 모두 사용됩니다.** 

- Sheet: 촉매가 벽면에 코팅되므로 표면적이 중요한 경우
- Network: 유동 관통이 보장되어 ΔP 예측이 안정적

논문에서는 "주기경계 해석의 일관성을 위해 Network 타입을 채택하였다. Sheet 타입은 Z 관통이 보장되지 않아 주기경계 적용이 제한적이다"로 기술하면 자연스럽습니다.

**또는** Sheet을 유지하되, 도메인 양 끝에 빈 버퍼(Gyroid 없는 유체 영역)를 두고 velocity inlet/outlet을 사용하는 방법도 있습니다. 다만 이 경우 ΔP 표현 한계(Δρ 문제)가 재발하므로 **Network + 주기BC가 가장 깔끔한 선택**입니다.

---

## 6. 3-g 재실행 결과 분석 (K 음수 진단)

### 6.1 현상

plan_2.5V §3 수정(Sheet→Network 기본값) 이후 `run_gyroid_3ghsv_plan191v.py` 재실행 결과:

```
[결과] g=1.0e-06, u_mean=-0.0000 m/s, dP=0.0127 Pa, K=-2.7155e-10 m²
```

- K 음수 = 유동이 반대로 흐르거나 안 흐른다는 뜻. 이전 Sheet 문제와 동일한 증상.

### 6.2 핵심 의문: Network 수정이 반영됐는가?

- 이전 결과(Guo 수정 전): K = -5.29e-10
- 이번 결과(Guo 수정 후): K = -2.72e-10
- 값이 달라졌으므로 Guo 수정은 반영된 새 실행.
- **그러나 Network 수정은 반영 안 됐을 가능성이 높음.**

### 6.3 확인 방법

```bash
grep -i "network\|sheet\|gyroid_type" scripts/run_gyroid_3ghsv_plan191v.py
```

- `gyroid_type="network"`가 명시되어 있는지 확인.
- **결과: 3인자 호출만 사용 (`w.set_geometry_gyroid_kernel(A_MM, T, WALL_VOXELS)`).**
- 기본값이 `"network"`로 바뀌었으므로 이론상 Network가 적용되어야 하지만, 확실성을 위해 **명시적으로 추가해야 함.**

### 6.4 추가 검증: 연결성 진단

```bash
python scripts/diag_gyroid_connectivity.py 2>&1
```

- `n_through = 0` → 여전히 Sheet 적용 중. 스크립트 수정 후 재실행 필요.
- `n_through > 0` → Network 적용됨. 다른 원인 추가 조사 필요.

### 6.5 조치

1. `run_gyroid_3ghsv_plan191v.py`에 `gyroid_type="network"` **명시적 추가**.
2. 연결성 진단으로 Network 마스크 확인.
3. Network 확인 후 3-g 재실행.

---

## 체크리스트

| 순서 | 항목 | 설명 | 상태 |
|------|------|------|------|
| 1 | 연결성 진단 | `diag_gyroid_connectivity.py` 실행 | ☐ |
| 2 | pyvista 시각화 | `visualize_gyroid_diag.py` → PNG 3~4장 | ☐ |
| 3 | VTI 수집 | `save_vti_gyroid_diag.py` → VTR 7개 | ☐ |
| 4 | PNG 확인 (사용자) | §2.4 표 4항목 | ☐ |
| 5 | 원인 확정 + 수정 | Sheet→Network 또는 방향 수정 | ☐ |
| 6 | Gyroid 3-g (5k 우선) | 5k에서 K 안정 시 판정, 미수렴 시 20k 연장 | ☐ |
| 7 | GCI 3-level | GCI < 5% | ☐ |
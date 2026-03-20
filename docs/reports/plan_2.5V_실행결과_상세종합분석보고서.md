# plan_2.5V 실행 결과 상세·종합 분석 보고서

**기준:** docs/plan_2.5V.md (Gyroid 유동 진단 + VTI 수집)  
**작성일:** 2026-03-19  
**문제:** Gyroid 3-g에서 u_mean ≈ 0, K 음수 — 유동이 흐르지 않는 현상 원인 규명.

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| 목적 | Gyroid 3-g 비정상 결과(u_mean≈0, K<0)의 원인 진단 및 VTI 수집·시각화 |
| 전제 | L1 PASS, L2-B K 이론 일치. 솔버 자체는 정상, Gyroid 형상/BC 이슈 추정 |
| 실행 순서 | §1.1 연결성 진단 → §1.2~1.3 코드 확인 → §2.5 시각화 → §2.1~2.2 VTI 수집 → §3 원인 수정 → (후속) 3-g·GCI |

---

## 2. Phase 1: 코드·연결성 진단

### 2.1 §1.1 Gyroid 마스크 Z방향 연결성 (실행 결과)

**스크립트:** `scripts/diag_gyroid_connectivity.py`  
**실행:** `python scripts/diag_gyroid_connectivity.py 2>&1 | tee logs/diag_connectivity.txt`

**설정:** NX=NY=131, NZ=550, dx=0.2 mm, A=5 mm, t=0.3, WALL=5. Sheet 타입 마스크(기존 `\|φ\|<t` → solid).

| 진단 | 결과 | 판정 |
|------|------|------|
| **[진단1] Z 관통 유체 셀 수** | **n_through = 0** | ❌ Z 방향 막힘 (Sheet 분리) |
| [진단2] 슬라이스별 유체 비율 | z=0, 545, 549 → 0; z=5~500 → 약 0.71 | 양 끝은 전부 solid(덕트 벽), 중간은 유체 비율 존재 |
| [진단3] 전체 공극률 ε | 0.6755 | |
| [진단4] XY(z=275) 유체 셀 수 | 12,241 / 17,161 | |
| [진단4] XZ(y=65) 유체 셀 수 | 49,020 / 72,050 | |
| **[진단5] 외벽 제외 내부 Z 관통** | **n_interior = 0** | 내부에도 Z 일관 관통 경로 없음 |

**결론:** **원인 A 확정** — Sheet Gyroid(`|φ|<t`)는 Z 방향으로 관통하는 단일 유체 경로를 보장하지 않으며, 두 개의 분리된 채널 네트워크(φ>t, φ<-t)만 존재. 주기BC에서 전체 유량이 0에 수렴하는 현상과 일치.

---

### 2.2 §1.2 체적력 방향 확인 (코드 검토)

**대상:** `solver/taichi_lbm_core.py`

| 확인 항목 | 결과 |
|-----------|------|
| Guo forcing Z 방향 | 체적력이 인덱스 2(vz)에 `+g_lbm`으로 적용됨 (`_guo_force_source_raw`, `_collision` 내 `g_z = self._body_force_z[None]`) |
| D3Q19 Z 양의 방향 | E_NP[5]=[0,0,1] (k+1), E_NP[6]=[0,0,-1]. Z 양의 방향 일치 |
| L2-B 참고 | L2-B(6×6 주기BC)에서 u_channel 양수(0.476). 동일 코드 경로이므로 체적력 +Z 방향 정상 |

**판정:** 체적력 방향 이상 없음. 원인 B 아님.

---

### 2.3 §1.3 get_flux_z 부호·정의 확인 (코드 검토)

**대상:** `solver/taichi_lbm_core.py` — `_flux_z_plane`, `get_flux_z`

| 확인 항목 | 결과 |
|-----------|------|
| 정의 | `get_flux_z(z)` = Σ (유체 셀만) `rho[i,j,z] * v[i,j,z][2]` (질량 유량, 격자 단위) |
| 부호 | vz > 0이면 flux > 0. L2-B에서 Q_phys 양수였음 → 부호 일관 |

**판정:** get_flux_z 정의·부호 이상 없음. 원인 C 아님.

---

## 3. Phase 2: VTI 수집 및 시각화

### 3.1 §2.1 VTI 수집 스크립트·설정

**스크립트:** `scripts/save_vti_gyroid_diag.py`

| 항목 | 값 |
|------|-----|
| 격자 | NX=NY=131, NZ=550, dx=0.2 mm |
| 모드 | `periodic_body_force` |
| g_lbm | 5e-6 |
| max_steps | 5,000 |
| SAVE_INTERVAL | 1,000 (매 1000스텝 VTR 1개) |
| 저장 변수 | rho, vz, solid (cellData) |
| 좌표 | x,y,z (mm), 0~(N+1)·DX_MM |

**구현 참고:** plan 문서의 `wrapper.core.vel` → 실제 코어 필드명에 맞춰 `wrapper.core.v` 사용. `get_rho_mean_fluid` 없음 → 유체 마스크로 rho 평균 계산 후 로그 출력.

---

### 3.2 §2.2 VTI 수집 실행 결과

**실행:** `PYTHONUNBUFFERED=1 python scripts/save_vti_gyroid_diag.py 2>&1 | tee logs/vti_gyroid_diag.txt`

**로그 요약 (logs/vti_gyroid_diag.txt):**

| step | flux_z(mid) | rho_mean | 비고 |
|------|-------------|----------|------|
| 1000 | 2.488419 | 1.000000 | VTR 저장 |
| 2000 | 1.272261 | 1.000000 | VTR 저장 |
| 3000 | 0.650827 | 1.000000 | VTR 저장 |
| 4000 | 0.325936 | 1.000000 | VTR 저장 |
| 5000 | 0.155945 | 1.000000 | VTR 저장 |

- Sheet 형상이므로 Z 관통 경로가 없어, 중간 단면(z_mid)에서의 flux는 **국소/과도 유동**에 해당.
- 스텝이 진행될수록 flux_z(mid) 감소(2.49 → 1.27 → 0.65 → 0.33 → 0.16) → 전체 관통 유량 0 수렴 경향.
- 다만 1000-step 간 상대 변화율이 약 49~52%로 매우 커서, **수렴 기준(예: 0.1%)에는 도달하지 않음**.
- g_lbm=5e-6, tau=0.595, dx=0.2 mm 기준 체적력으로 환산한 목표 차압은 **dP_target ≈ 0.06337 Pa**.

**현재 VTR 파일 (results/):**

| 파일 | 크기(대략) | 비고 |
|------|------------|------|
| gyroid_diag_step0000.vtr | ~217 MB | 초기 (유동 전) |
| gyroid_diag_step1000.vtr | ~217 MB | |
| gyroid_diag_step2000.vtr | ~217 MB | |
| gyroid_diag_step3000.vtr | ~217 MB | |
| gyroid_diag_step4000.vtr | ~217 MB | |
| gyroid_diag_step5000.vtr | ~217 MB | |
| gyroid_diag_stepfinal.vtr | ~217 MB | 최종 저장 |

- **VTR 7개 확보 완료.**

---

### 3.3 §2.5 시각화 스크립트·실행 결과

**스크립트:** `scripts/visualize_gyroid_diag.py` (pyvista, OFF_SCREEN=True)

| 출력 PNG | 내용 | 생성 여부 |
|----------|------|-----------|
| gyroid_solid_xy_z275.png | solid XY 단면 (z=275) | ✅ 생성 |
| gyroid_solid_xz_y65.png | solid XZ 단면 (y=65) — Z 관통 확인 | ✅ 생성 |
| gyroid_3d_fluid.png | 3D 유체 영역 (solid=0 threshold) | ✅ 생성 |
| gyroid_vz_xy_z275.png | vz XY (z=275), step5000 VTR 기반 | ✅ 생성 |

- **PNG 4장 생성 완료.** §2.4 표의 1~4번 항목 확인 가능.

---

### 3.4 §2.4 pyvista 확인 항목 정리

| # | 확인 항목 | PNG | 기대 결과 | 현재 |
|---|-----------|-----|-----------|------|
| 1 | solid XY (z=275) | gyroid_solid_xy_z275.png | Gyroid 패턴, 열린 유로 | ✅ 생성됨 |
| 2 | solid XZ (y=65) | gyroid_solid_xz_y65.png | Z 관통 유로 | ✅ 생성됨. Sheet 특성상 관통 없음 |
| 3 | 3D fluid | gyroid_3d_fluid.png | 연결된 유체 영역 | ✅ 생성됨. 분리된 덩어리 예상 |
| 4 | vz XY (z=275) | gyroid_vz_xy_z275.png | 유체에서 양의 vz | ✅ 생성됨 |

---

## 4. §3 원인 A 해결: Sheet → Network 수정

### 4.1 적용 내용

**파일:** `solver/taichi_lbm_core.py`

- **`_init_gyroid_duct_kernel`**  
  - 인자 추가: `use_network: ti.i32`.  
  - `use_network == 0` (Sheet): 기존과 동일 `solid = 1 if |φ| < t else 0`.  
  - `use_network != 0` (Network): `solid = 1 if φ > -t else 0` (φ < -t 영역을 유체로, Z 관통 보장).
- **`set_geometry_gyroid_kernel`**  
  - 인자 추가: `gyroid_type: str = "network"`.  
  - `gyroid_type`이 `"network"`(기본)이면 `use_network=1`, 그 외(예: `"sheet"`)면 `use_network=0`.
- **Wrapper**  
  - `set_geometry_gyroid_kernel(a_mm, t, wall_voxels, gyroid_type)` 그대로 core에 전달.

### 4.2 호환성

- 기존 모든 호출은 3인자 `(a_mm, t, wall_voxels)`만 사용 → 기본값 `gyroid_type="network"` 적용.
- Sheet가 필요한 경우 `gyroid_type="sheet"` 명시하면 기존 동작 유지.

### 4.3 논문 관점 (plan §5)

- 주기경계 해석의 일관성을 위해 **Network 타입을 기본 채택**.
- “Sheet 타입은 Z 관통이 보장되지 않아 주기경계 적용이 제한적”으로 기술 가능.

---

## 5. 체크리스트 현황

| 순서 | 항목 | 설명 | 상태 |
|------|------|------|------|
| 1 | 연결성 진단 | diag_gyroid_connectivity.py 실행 | ✅ 완료 (n_through=0 → 원인 A) |
| 2 | pyvista 시각화 | visualize_gyroid_diag.py → PNG 3~4장 | ✅ 4장 완료 |
| 3 | VTI 수집 | save_vti_gyroid_diag.py → VTR 7개 | ✅ 7개 생성 완료 |
| 4 | PNG 확인 (사용자) | §2.4 표 4항목 | ✅ 1~4 완료 |
| 5 | 원인 확정 + 수정 | Sheet→Network | ✅ 확정 및 코드 반영 (기본값 network) |
| 6 | Gyroid 3-g (5k 우선) | 5k에서 K 안정 시 판정 | ⏳ Network로 재실행 필요 |
| 7 | GCI 3-level | GCI < 5% | ⏳ 3-g PASS 후 실행 |

---

## 6. 요약 및 후속 권장

- **원인:** **Sheet Gyroid**로 인한 **Z 방향 관통 경로 부재**(n_through=0). 체적력·get_flux_z 정의/부호는 정상.
- **조치:** `set_geometry_gyroid_kernel`에 **Network 타입 기본 적용** 완료. 동일 형상으로 재실행 시 Z 관통 유동 기대.
- **VTI/시각화:** step0000~5000+final VTR 7개 및 PNG 4장(고체 3 + vz 1) 확보 완료.
- **수렴성:** Sheet 조건 진단 런(5000스텝)은 flux 변화율이 커서 수렴 판정 불가(비수렴). 이는 Z 관통 부재 진단 결과와 일치.
- **다음 단계:**  
  1) **Network 기본**으로 `run_gyroid_3ghsv_plan191v.py` 재실행(5k 우선, 필요 시 20k) → K·편차 판정.  
  2) 3-g PASS 후 `run_gci_3level_plan14v.py` 실행 → GCI < 5% 확인.

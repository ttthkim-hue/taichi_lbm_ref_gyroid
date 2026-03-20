# SCI 논문 계획서 v1.1
## Gyroid TPMS 구조화 촉매 지지체 유동 최적화
### Taichi LBM 시뮬레이션 + Bayesian Optimization 기반 설계

**최종 수정일** | 2026년 3월 17일  
**연구자** | 김태형 (KILAM)

---

## 1. 연구 개요

### 1.1 배경 및 목적

SCR(Selective Catalytic Reduction) 탈질 촉매의 효율을 극대화하기 위해 3D 프린팅이 가능한 Gyroid TPMS(Triply Periodic Minimal Surface) 구조를 도입한다. 본 연구는 **Taichi 기반 LBM(Lattice Boltzmann Method) 시뮬레이션**과 **Bayesian Optimization(BO)**을 결합하여, 촉매의 핵심 성능 지표인 **비표면적(Surface Area) 최대화**와 **압력 손실(ΔP) 최소화** 사이의 Pareto 최적해를 도출하는 것을 목적으로 한다.

### 1.2 형상·시뮬레이션 파이프라인 (STL to Voxel 미채택)

본 연구에서는 **STL → Voxel 변환 파이프라인은 사용하지 않는다.** 현재 3종 형상 STL(빈 덕트, Reference 6×6, Gyroid)은 연구자가 확인용으로 만들어 둔 것이며, 형상 기준으로는 확정된 상태다.

| Step | 내용 |
|------|------|
| Step 1 | 형상을 **Taichi 커널**에 직접 반영 (수식 기반 마스크 또는 .npy 마스크 주입) |
| Step 2 | Taichi LBM으로 유동 해석 수행 후, 결과를 **NumPy**로 추출 |
| Step 3 | 필요 시 NumPy 기반 형상/결과를 **OpenSCAD로 STL화**하여 최종 검증용으로 활용 |

즉, **Taichi 커널 → NumPy 추출 → OpenSCAD STL(최종 검증)** 순으로 정리한다.

---

## 2. 물리 파라미터 및 운전 조건 (200°C 공기)

| 파라미터 | 값 | 비고 |
|----------|-----|------|
| 동점성계수 ν | 3.52 × 10⁻⁵ m²/s | 200°C 건조공기 물성 |
| 밀도 ρ | 0.746 kg/m³ | 1 atm 기준 |
| 동역학점성계수 μ | 2.626 × 10⁻⁵ Pa·s | ν × ρ |
| 유입 유속 u_in | 0.2778 m/s | GHSV 10,000 h⁻¹ 기준 |
| 도메인 크기 | 25.4 × 25.4 × 110 mm | 1인치 관체, 촉매층 100 mm |

---

## 3. Bayesian Optimization (BO) 설정

### 3.1 설계 변수 및 제약 조건

- **설계 변수**
  - 단위 셀 크기 **a ∈ [3, 8] mm**
  - 두께 오프셋 **t ∈ [-0.5, 0.5]**
- **기하학적 제약**
  - 공극률 **ε ∈ [0.35, 0.65]**
  - 최소 벽 두께 **≥ 1.0 mm** (BJT 공정 해상도 고려)

### 3.2 목적함수 (Multi-Objective)

단순 투과율(K) 대신, 물리적으로 상충 관계에 있는 지표를 설정하여 유의미한 Pareto Frontier를 탐색한다.

| 목적 | 지표 | 설명 |
|------|------|------|
| **f₁** (최대화) | 비표면적 S_v [m²/m³] | 반응 기여도 평가 |
| **f₂** (최소화) | 압력 강하 ΔP [Pa] | 송풍기 동력 손실 평가 |
| **f₃** (최소화) | 속도 균일도 CV | 채널 내 편류 발생 억제 평가 |

---

## 4. Taichi LBM 수치 설정

| 항목 | 설정값 | 비고 |
|------|--------|------|
| Solver | D3Q19 MRT-LBM | 유동 안정성 및 격자 독립성 확보 |
| 격자 해상도 (dx) | 0.2 mm | 격자 수: **127 × 127 × 550** (= 8.87M nodes) |
| Relaxation τ | 0.595 | 0.5 < τ < 1.0 안정 범위 준수 |
| Mach Number (Ma) | 0.087 | 비압축성 근사 유효 (Ma < 0.1) |
| 결과 포맷 | VTI (VTK ImageData) | ParaView 시각화 및 정밀 후처리 |

**plan_1.2V 교차검증 결과:** τ, dx, ν로부터 dt 역산 시 dt = 3.60×10⁻⁵ s, u_lbm = 0.0500, Ma = 0.0866 ≈ 0.087 → 계획서 값과 정합. 물성(ν, ρ, μ) 및 GHSV→u_in 변환도 검증됨.

---

## 5. 수치 안정성·검증 체계 (plan_1.2V 반영)

### 5.1 MRT 구현 및 τ

- τ = 0.595는 **MRT-LBM**에서 허용. BGK(SRT)만 쓰면 불안정 가능 → **코드 내 MRT S-matrix 구현 여부 반드시 확인**.
- 질량 보존: 매 N스텝 입출구 유량·총 질량 드리프트 모니터링 (< 0.1%). STL watertight·voxel 누수 검사 필수.
- 벽 두께: dx=0.2 mm 기준 **최소 3 voxel (0.6 mm)** 이상 권장. 1 mm 벽 = 5 voxel.

### 5.2 격자 독립성 (GCI)

SCI 논문 필수. 3단계 격자로 GCI 산출 권장.

| Level | dx (mm) | 격자 | 노드 수 | 비고 |
|-------|---------|------|---------|------|
| Coarse | 0.4 | 64×64×275 | 1.13M | |
| Medium (기준) | 0.2 | 127×127×550 | 8.87M | 현재 계획 |
| Fine | 0.15 | 169×169×733 | 20.9M | 16GB GPU 내 수용 가능 |

### 5.3 검증 레벨 (L1~L4)

| Level | 내용 | 상태 |
|-------|------|------|
| L1 | 빈 덕트 ΔP vs Hagen-Poiseuille (정사각 단면 보정) | ⚠️ 미확정 |
| L2 | Reference 6×6 ΔP/K/CV vs 이론·해석 | ❌ 미완 |
| L3 | 격자 독립성 (GCI) | ❌ 미계획 |
| L4 | 질량 보존 검증 (시간 추이) | ❌ 미계획 |

L1~L4 완료 후 BO·논문 진행 권장.

### 5.4 빈 덕트 예제 검증 (물리 엔진 벤치마킹)

Taichi LBM 물리 엔진의 신뢰도를 확보하기 위해, **빈 덕트 예제**를 **OpenLB 공식 예제** 및 **Taichi LBM 공식(또는 공개) 예제**와 벤치마킹한다.

| 항목 | 내용 |
|------|------|
| 목적 | 동일 조건(빈 덕트, Re·ΔP·경계조건)에서 OpenLB·Taichi LBM 예제 결과와 비교하여 물리 엔진(압력강하, 유량, BC) 검증 |
| 대상 | OpenLB 공식 튜토리얼/예제, Taichi LBM 관련 공식·벤치마크 예제 |
| 산출물 | 벤치마크 조건 정리, ΔP·유량 비교표, 불일치 시 원인 분석 및 조치 |
| 위치 | L1(Hagen-Poiseuille) 검증의 전제 또는 병행: 공식 예제와 일치한 뒤 우리 도메인(25.4×25.4×110 mm) L1 수행 |

이 단계를 거쳐 Taichi LBM 솔버가 공식 예제 수준의 물리 정확도를 갖는지 확인한 후, Reference 6×6·Gyroid BO로 확장한다.

---

## 6. 코드 파이프라인 구조

```
project_root/
├── geometry/
│   └── (형상은 Taichi 커널 또는 .npy 마스크로 주입; STL은 확인용·OpenSCAD 최종검증용)
├── solver/
│   ├── taichi_lbm_core.py     # Taichi 기반 D3Q19 LBM 연산 엔진 (GPU 가속)
│   └── post_process.py        # Delta P, S_v, CV 산출, NumPy 추출, VTI 저장
├── optimization/
│   ├── bo_engine.py           # BoTorch 기반 Pareto 최적화 수행
│   └── run_experiment.py      # 전체 파이프라인 제어 루프
└── results/
    ├── vtk_plots/             # 시뮬레이션 유동장 시각화 결과
    ├── pareto_data.csv        # 최적화 결과 데이터베이스
    └── (NumPy 추출 결과 → OpenSCAD STL화로 최종 검증)
```

*(STL to Voxel은 채택하지 않음. 3종 형상 STL은 확인용 확정. Taichi 커널 → NumPy → OpenSCAD STL 최종검증 흐름. 현재 프로젝트에는 geometry_openscad/, 아카이브 taichi_lbm_solver_v3.py 등이 있으며, 통합 시 위 구조로 정리 예정.)*

---

## 7. Taichi LBM 검증 현황 (빈 덕트, Reference 6×6)

### 7.1 빈 덕트 (Empty Duct)

| 항목 | 상태 | 비고 |
|------|------|------|
| 형상·STL (확인용) | ✅ 확정 | `geometry_openscad/empty_duct_v32.scad` (.stl) — 25.4×25.4×110 mm, 1 mm 벽. 3종 형상 STL 중 하나. |
| Taichi 주입 | ✅ 가능 | 형상은 Taichi 커널 또는 .npy 마스크로 주입 (STL→Voxel 미사용) |
| Taichi LBM 실행 | ⚠️ 진행됨 | `Results_EmptyDuct_200C_v2`, `Results_EmptyDuct_v3` 등 시뮬 로그 존재 |
| **물리 엔진 벤치마킹** | ❌ **미반영** | **OpenLB·Taichi LBM 공식 예제와 빈 덕트 벤치마킹**으로 물리 엔진 검증 계획 필요 → §5.4 반영 |
| 검증 완료 여부 | ⚠️ **미확정** | 벤치마킹 후 ΔP vs Hagen-Poiseuille 등 L1 검증 스크립트 실행·PASS 판정 문서화로 최종 확정. |

### 7.2 Reference 6×6

| 항목 | 상태 | 비고 |
|------|------|------|
| 형상·STL (확인용) | ✅ 확정 | `geometry_openscad/reference_6x6_v32.scad` (.stl) — Main 구간 6×6 채널, 내벽 1 mm. 3종 형상 STL 중 하나. |
| Taichi 주입 | ✅ 가능 | 형상은 Taichi 커널 또는 .npy 마스크로 주입 |
| Taichi LBM 실행 | ⚠️ **미완** | `Results_Ref_dx02` 폴더는 존재하나, Reference 6×6에 대한 Taichi LBM 검증 완료 문서·판정 없음. OpenLB Reference 검증(V4)은 별도. |
| 검증 완료 여부 | ❌ **미완** | Taichi LBM으로 Reference 6×6 K/ΔP/CV 시뮬 및 이론·해석 비교 검증 미완. |

### 7.3 요약

- **빈 덕트**: 형상(STL 확인용)·Taichi 주입·시뮬 실행은 준비됨. **물리 엔진 검증**을 위해 OpenLB·Taichi LBM 공식 예제와 빈 덕트 벤치마킹(§5.4) 수행 후, L1 검증 스크립트 실행 및 PASS 판정 문서화로 “완료” 확정.
- **Reference 6×6**: 형상(STL 확인용)·Taichi 주입 경로 준비됨. Taichi LBM 기준 Reference 6×6 검증은 미완. BO/논문 전 Reference 6×6 시뮬·검증 수행 권장.

---

## 8. GPU·연산 시간 및 타임라인 (plan_1.2V 반영)

**대상 GPU:** NVIDIA RTX 5060 Ti 16GB.

- **메모리:** 127×127×550 ≈ 8.87M nodes → 약 2.2 GB (필드·VTI·런타임 포함). Fine 격자(0.15 mm)까지 16GB 내 수용 가능.
- **단일 케이스:** 수렴까지 ~55,000 steps 가정 시 **약 70 min** (형상 주입·후처리 포함 시 **~75 min/iteration**).
- **타임라인 제안 (7주):** 1주 코드 통합·L1 검증 → 2주 L2·격자 독립성 → 3주 BO 테스트 → 4주 BO 본 실행 → 5주 Pareto 분석·시각화 → 6~7주 논문 집필.

---

## 9. 잠재적 문제·위험 요소 (plan_1.2V 반영)

| 우선순위 | 위험 | 대책 |
|----------|------|------|
| 1 | MRT가 실제로 BGK로 동작 | S-matrix 확인, MRT vs BGK 테스트 |
| 2 | Voxelization 누수(얇은 벽) | (a,t)별 벽 두께 ≥ 3 voxel 사전 검증 |
| 3 | L1 빈 덕트 검증 미완 | Hagen-Poiseuille 비교 즉시 실행·문서화 |
| 4 | 격자 독립성 미계획 | 3-level GCI 스터디 추가 |
| 5 | 국소 Ma 초과(좁은 채널) | 후처리 max(Ma) 모니터링 |

**형상·후처리:** 좌표계·덕트+Gyroid 정합 확인. NumPy 추출 후 OpenSCAD STL로 최종 검증 시 정합성 확인. **후처리:** ΔP 측정 구간(입출구 발달 구간 제외), S_v·CV 정의 명확화.

---

## 10. Todolist 요약 (plan_1.1V + plan_1.2V 반영)

| ID | 항목 | 상태 |
|----|------|------|
| V-geo | 3종 형상 STL (빈 덕트 / Ref 6×6 / Gyroid) 확인용 확정. Taichi 커널→NumPy→OpenSCAD STL | 형상 확정, 파이프라인 정리됨 |
| V-bench | 빈 덕트 예제 검증: OpenLB·Taichi LBM 공식 예제 벤치마킹 (물리 엔진 검증) | **§5.4 반영, 수행 필요** |
| V-MRT | MRT S-matrix 구현 여부 확인 (BGK 대비) | **필수** |
| V-duct | 빈 덕트 L1 검증 (ΔP vs Hagen-Poiseuille). 벤치마킹 후 판정 문서화 | 진행됨, **벤치마킹·판정 문서화 후 완료** |
| V-ref | Reference 6×6 L2 검증 (K/ΔP/CV) | **미완** |
| V-GCI | 격자 독립성 3-level GCI 스터디 | **미계획** |
| V-mass | 질량 보존·유량 밸런스 모니터링 | **미계획** |
| BO | Bayesian Optimization (a, t, S_v, ΔP, CV) | 파이프라인 정리됨. 2-objective(S_v, ΔP) 권장 |
| Paper | 논문 작성 및 PiAM 투고 | 목표 |

---

## 부록: plan_1.1V · plan_1.2V 대조

- **docs/plan_1.1V.md:** 솔버 Taichi LBM, 형상 Taichi 커널→NumPy→OpenSCAD STL 최종검증(STL→Voxel 미채택), 목적함수 f₁ S_v / f₂ ΔP / f₃ CV, 격자 127×127×550·dx=0.2 mm·τ=0.595·Ma=0.087, 코드 구조.
- **docs/plan_1.2V.md:** 상세 검토 보고서 — 물리 파라미터 교차검증(dt·Ma·물성·GHSV), 수치 안정성(MRT/τ, 질량 보존, voxel 정밀도), GPU·연산 시간, 검증 체계 L1~L4·격자 독립성, 잠재적 문제·위험 요소, 타임라인 7주. 본 최종 계획서에 위 내용을 반영함.

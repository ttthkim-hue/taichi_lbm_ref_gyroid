SCI 논문 계획서 v1.1Gyroid TPMS 구조화 촉매 지지체 유동 최적화Taichi LBM 시뮬레이션 + Bayesian Optimization 기반 설계최종 수정일 | 2026년 3월 17일연구자 | 김태형 (KILAM)1. 연구 개요1.1 배경 및 목적SCR(Selective Catalytic Reduction) 탈질 촉매의 효율을 극대화하기 위해 3D 프린팅이 가능한 Gyroid TPMS(Triply Periodic Minimal Surface) 구조를 도입한다. 본 연구는 Taichi 기반 LBM(Lattice Boltzmann Method) 시뮬레이션과 **Bayesian Optimization(BO)**을 결합하여, 촉매의 핵심 성능 지표인 비표면적(Surface Area) 최대화와 압력 손실($\Delta P$) 최소화 사이의 Pareto 최적해를 도출하는 것을 목적으로 한다.1.2 핵심 자동화 파이프라인: STL to Voxel실제 BJT(Binder Jet 3D Printing) 공정과의 정합성을 확보하기 위해, 수식 기반 생성 대신 STL 파일을 격자화(Voxelization)하여 시뮬레이션에 주입하는 방식을 채택한다.Step 1: Python(Trimesh) 또는 OpenSCAD를 통한 설계 변수($a, t$) 기반 STL 생성.Step 2: trimesh의 voxelize 기능을 활용하여 STL 표면을 직교 격자 데이터로 변환 (0=Fluid, 1=Solid).Step 3: 변환된 Voxel 데이터를 Taichi Field에 직접 매핑하여 GPU 가속 LBM 연산 수행.2. 물리 파라미터 및 운전 조건 (200°C 공기)파라미터값비고동점성계수 $\nu$$3.52 \times 10^{-5} \, m^2/s$200°C 건조공기 물성밀도 $\rho$$0.746 \, kg/m^3$1 atm 기준동역학점성계수 $\mu$$2.626 \times 10^{-5} \, Pa \cdot s$$\nu \times \rho$유입 유속 $u_{in}$$0.2778 \, m/s$GHSV 10,000 $h^{-1}$ 기준도메인 크기$25.4 \times 25.4 \times 110 \, mm$1인치 관체, 촉매층 100mm3. Bayesian Optimization (BO) 설정3.1 설계 변수 및 제약 조건설계 변수: * 단위 셀 크기 $a \in [3, 8] \, mm$두께 오프셋 $t \in [-0.5, 0.5]$기하학적 제약: * 공극률 $\epsilon \in [0.35, 0.65]$최소 벽 두께 $\ge 1.0 \, mm$ (BJT 공정 해상도 고려)3.2 목적함수 (Multi-Objective)단순 투과율($K$) 대신, 물리적으로 상충 관계에 있는 지표를 설정하여 유의미한 Pareto Frontier를 탐색한다.$f_1$ (최대화): 비표면적 ($S_v, m^2/m^3$) — 반응 기여도 평가$f_2$ (최소화): 압력 강하 ($\Delta P, Pa$) — 송풍기 동력 손실 평가$f_3$ (최소화): 속도 균일도 ($CV$) — 채널 내 편류 발생 억제 평가4. Taichi LBM 수치 설정항목설정값비고SolverD3Q19 MRT-LBM유동 안정성 및 격자 독립성 확보격자 해상도 ($dx$)$0.2 \, mm$격자 수: $127 \times 127 \times 550$Relaxation $\tau$$0.595$$0.5 < \tau < 1.0$ 안정 범위 준수Mach Number ($Ma$)$0.087$비압축성 근사 유효 ($Ma < 0.1$)결과 포맷VTI (VTK ImageData)ParaView 시각화 및 정밀 후처리5. 코드 파이프라인 구조project_root/
├── geometry/
│   ├── stl_generator.py       # a, t 기반 Gyroid STL 생성 (OpenSCAD/Trimesh)
│   └── voxelizer.py           # STL to Numpy Voxel 변환 (Taichi 주입용)
├── solver/
│   ├── taichi_lbm_core.py     # Taichi 기반 D3Q19 LBM 연산 엔진 (GPU 가속)
│   └── post_process.py        # Delta P, S_v, CV 산출 및 VTI 저장
├── optimization/
│   ├── bo_engine.py           # BoTorch 기반 Pareto 최적화 수행
│   └── run_experiment.py      # 전체 파이프라인 제어 루프
└── results/
    ├── vtk_plots/             # 시뮬레이션 유동장 시각화 결과
    └── pareto_data.csv        # 최적화 결과 데이터베이스

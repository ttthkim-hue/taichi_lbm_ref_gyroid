# Taichi LBM Reference·Gyroid 재검증 보고서 (초안 구조)

본 문서는 Taichi LBM으로 수행한 Reference 채널 및 Gyroid 채널 검증 결과를
정리하기 위한 골격입니다. 실제 수치는 시뮬레이션 완료 후 채워 넣습니다.

## 1. 문제 설정

- 형상
  - Reference 채널: OpenLB `ref_dx02.dat`와 동등한 6×6 채널
  - Gyroid 채널: `openlb_gyroid/results/gate_a/gyroid_dx02_v3.dat`
- 유동 조건
  - u_inlet = 0.2778 m/s
  - L = 0.1 m
  - ν = 3.52e-5 m²/s, ρ = 0.746 kg/m³
  - τ ≈ 0.557 (UnitConverter로 설정)

## 2. 수치 세팅 (Taichi vs OpenLB)

- 격자 해상도, dx, dt, τ, u_latt, Ma 비교
- 경계조건
  - OpenLB: InterpolatedPressure + pressure ramp
  - Taichi: velocity/pressure 혼합 BC 및 ramp 스킴

## 3. Reference 채널 결과

| 항목          | OpenLB           | Taichi LBM       | 비고              |
| ------------- | ---------------- | ---------------- | ----------------- |
| K [m²]        |                  |                  | rel err [%]       |
| ΔP [Pa]       |                  |                  | rel err [%]       |
| CV            |                  |                  | abs diff          |
| converged     | true/false       | true/false       |                   |
| mass drift    | -                |                  | ρ 합 변화 비율    |
| flux balance  | -                |                  | in/out 불균형 비율 |

## 4. Gyroid 채널 결과

동일 형식의 표를 사용하여 K, ΔP, CV, 수렴 여부를 비교.

## 5. 논의

- Taichi LBM에서 mass conservation 및 ΔP·K·CV 일치성이 어느 정도 수준인지
- Reference 채널과 Gyroid 채널에서 나타난 차이의 원인 추정
- 향후 개선 필요 사항 (예: 더 정교한 BC, τ/Ma 조정, 해상도 변경 등)

## 6. 결론

- Taichi LBM이 OpenLB 결과를 재현하는 정도를 요약
- 이후 최적화/설계 단계에서 Taichi LBM 활용 가능성 평가


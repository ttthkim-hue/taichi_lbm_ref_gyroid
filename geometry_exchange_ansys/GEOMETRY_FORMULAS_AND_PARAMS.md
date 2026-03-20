# 형상 수식 및 파라미터 (Geometry Formulas and Parameters)

ANSYS 등 타 CAD/CFD 툴에서 형상 재현 및 해석 시 참고용 문서입니다. 단위는 **mm** 기준입니다.

---

## 1. 공통 치수 (도메인)

| 항목 | 값 | 비고 |
|------|-----|------|
| 외부 단면 | 25.4 × 25.4 mm | 1 inch |
| 외벽 두께 | 1.0 mm | |
| 내부 유로 단면 | 23.4 × 23.4 mm | 25.4 − 2×1.0 |
| 전체 길이 (Z) | 110 mm | |
| 버퍼 구간 | 0~5 mm, 105~110 mm | Gyroid 없는 유체 영역 |
| 메인 구간 | 5~105 mm | Gyroid/채널 배치 구간 (100 mm) |

---

## 2. Reference 6×6 셀

- 내벽 두께: 1.0 mm
- 6×6 채널이 메인 구간(5~105 mm)에만 존재
- 채널 폭:

```text
CHANNEL_W = (23.4 - 5×1.0) / 6 = 3.067 mm
```

- 채널 주기(한 셀): `PERIOD = CHANNEL_W + 1.0` mm
- 입구/출구 버퍼(0~5 mm, 105~110 mm)는 비어 있는 유로

---

## 3. Gyroid Network (자이로이드)

### 3.1 수식

스칼라장 φ (단위: 없음):

```text
φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)
```

- **Solid (고체):** φ > −t  
- **Fluid (유체):** φ ≤ −t  

즉, **solid = φ > -t** 로 정의합니다. (Sheet 타입 `|φ| < t` 는 사용하지 않음.)

### 3.2 파라미터

| 기호 | 의미 | 단위 | 권장 범위 |
|------|------|------|-----------|
| a | 단위셀 크기 | mm | 3~8 |
| t | 두께 파라미터 (φ > −t 이면 고체) | — | 0.05~0.5 |

### 3.3 공극률 추정

근사식:

```text
ε ≈ 0.5 + t/3
```

(예: t=0.3 → ε ≈ 0.6)

---

## 4. LBM 대응

- Taichi LBM 쪽 설정과 동일한 수식/조건 사용:
  - `set_geometry_gyroid_kernel(a, t, gyroid_type="network")`  
  - Network 타입: solid = φ > −t
- STP/연속 형상과 LBM voxel 형상은 해상도 차이로 인해 **약 ±0.5·dx** 정도 오차 가능 (격자 분할에 따른 경계 위치 차이).

---

## 5. 전달 파일과의 대응

| 파일명 | 형상 | 비고 |
|--------|------|------|
| empty_duct_v32.step | 외부 25.4×25.4×110, 내부 23.4×23.4×110 공동 | B-Rep |
| reference_6x6_v32.step | 6×6 채널 + 입출구 버퍼 | B-Rep |
| gyroid_network_a5_t03.step | Network Gyroid (a=5 mm, t=0.3) + 외벽 덕트 | marching cubes → STEP |

파라미터 변경이 필요하면 `generate_gyroid_step.py` 를 사용해 새 STEP을 생성할 수 있습니다.

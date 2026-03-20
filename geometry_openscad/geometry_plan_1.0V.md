# 수정지시사항 — ANSYS STP 전달 패키지

**작성일:** 2026-03-19  
**대상:** `/mnt/h/taichi_lbm_ref_gyroid/geometry_exchange_ansys/` 전체

---

## 1. Gyroid 타입: Network 고정

모든 Gyroid 형상은 **Network 타입**으로 생성한다.

```
φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)

solid = φ > -t  (φ < -t 영역이 유체, Z 관통 보장)
```

Sheet 타입(`|φ| < t`)은 사용하지 않는다. 코드·문서에서 Sheet 관련 내용 제거.

---

## 2. 전달 포맷: STP만

STL은 제공하지 않는다. 모든 형상을 STP(STEP AP214)로 전달.

산출물:

```
geometry_exchange_ansys/
├── empty_duct_v32.step
├── reference_6x6_v32.step
├── gyroid_network_a5_t03.step          ← 현재 기준 형상
├── generate_gyroid_step.py             ← 파라미터 변경 생성기
├── GEOMETRY_FORMULAS_AND_PARAMS.md     ← 수식/파라미터/단위
└── README_ANSYS_DELIVERY.md            ← ANSYS import 안내
```

---

## 3. 도메인 치수: 1인치 (25.4mm) 고정

| 항목 | 값 |
|------|-----|
| 외부 단면 | 25.4 × 25.4 mm |
| 외벽 두께 | 1.0 mm |
| 내부 유로 | 23.4 × 23.4 mm |
| 전체 길이 | 110 mm |
| 버퍼 구간 | 0~5mm, 105~110mm (Gyroid 없는 유체 영역) |
| 메인 구간 | 5~105mm (Gyroid 배치) |

131격자(26.2mm)는 LBM voxel 균등 분할용이며, STP 물리 치수와 무관.

---

## 4. generate_gyroid_step.py — Network 기준 파라미터 생성기

### 4.1 CLI 인터페이스

```bash
# 기본 (현재 기준 형상)
python generate_gyroid_step.py

# 단위셀 크기 변경
python generate_gyroid_step.py --a 3

# 두께 파라미터 변경
python generate_gyroid_step.py --a 8 --t 0.1

# 해상도 변경 (면 밀도)
python generate_gyroid_step.py --a 5 --t 0.3 --res 80

# 출력 파일명 지정
python generate_gyroid_step.py --a 5 --t 0.3 --out my_gyroid.step
```

### 4.2 파라미터

| 인자 | 기본값 | 범위 | 설명 |
|------|--------|------|------|
| `--a` | 5.0 | 3~8 mm | 단위셀 크기 |
| `--t` | 0.3 | 0.05~0.5 | Network 두께 파라미터 (φ > -t → solid) |
| `--res` | 60 | 30~120 | Marching cubes 해상도 (셀/단위셀) |
| `--out` | 자동 | — | 출력 파일명 (미지정 시 `gyroid_network_a{a}_t{t}.step`) |
| `--with-duct` | True | — | 외벽 포함 (False면 Gyroid만) |
| `--buffer` | 5.0 | mm | 입출구 버퍼 길이 |

### 4.3 생성 파이프라인

```
1. Gyroid implicit function 평가 (numpy meshgrid)
2. Marching cubes → 삼각형 메쉬 (skimage)
3. 외벽 Boolean union (trimesh 또는 FreeCAD)
4. 버퍼 구간 (Gyroid 없는 빈 덕트) 결합
5. FreeCAD/OCC로 Solid 변환 → STEP 저장
6. 검증 로그 출력: 파일 크기, 면 수, bounding box, ε(공극률)
```

### 4.4 출력 로그 형식

```
[생성 완료]
  파라미터: a=5.0mm, t=0.3, type=network
  수식: solid = φ(x,y,z) > -0.3
  공극률 ε: 0.60 (추정)
  bounding box: 25.4 × 25.4 × 110.0 mm
  면 수: 284,531
  파일: gyroid_network_a5_t03.step (42.3 MB)
```

---

## 5. GEOMETRY_FORMULAS_AND_PARAMS.md 포함 내용

### 5.1 공통 치수

```
외부: 25.4 × 25.4 × 110 mm (1인치 관체)
외벽: 1.0 mm
버퍼: 5 mm (양쪽)
메인: 100 mm (5~105mm)
```

### 5.2 6×6 Reference

```
내부 격벽: 1.0 mm × 5개 (각 방향)
채널 폭: (23.4 - 5×1.0) / 6 = 3.067 mm
채널 수: 36
```

### 5.3 Gyroid Network

```
φ(x,y,z) = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)

Solid 조건: φ > -t
Fluid 조건: φ ≤ -t

파라미터:
  a [mm]: 단위셀 크기. 값이 작을수록 채널이 촘촘
  t [-]:  두께 파라미터. 값이 클수록 solid 비율 증가 (ε 감소)

ε 대략 추정: ε ≈ 0.5 + t/3 (t=0 → ε≈0.5, t=0.3 → ε≈0.6)
정확한 ε는 생성기 로그에서 확인
```

### 5.4 LBM 시뮬레이션과의 대응

```
STP 형상은 LBM Taichi 커널의 set_geometry_gyroid_kernel(a, t, gyroid_type="network")과
동일한 수식으로 생성됨. 파라미터 (a, t)가 같으면 형상이 동일.
단, STP는 연속 표면(marching cubes), LBM은 voxel 이산화이므로
벽면 위치에 ±0.5dx 차이 존재.
```

---

## 6. Gyroid STP 용량 대응

| res | 예상 면 수 | 예상 파일 크기 | 용도 |
|-----|-----------|---------------|------|
| 30 | ~50k | ~10 MB | 형상 확인/경량 검토 |
| 60 | ~280k | ~45 MB | **기본 (해석용)** |
| 120 | ~1.1M | ~180 MB | 고정밀 (필요 시) |

README에 "ANSYS SpaceClaim에서 import 시 Facets to BSurface 변환 권장, res=60 기본" 명시.

---

## 체크리스트

| 순서 | 항목 | 상태 |
|------|------|------|
| 1 | empty_duct B-Rep → STEP | ☐ |
| 2 | reference_6x6 B-Rep → STEP | ☐ |
| 3 | gyroid_network_a5_t03 → STEP | ☐ |
| 4 | generate_gyroid_step.py 작성 | ☐ |
| 5 | GEOMETRY_FORMULAS_AND_PARAMS.md | ☐ |
| 6 | README_ANSYS_DELIVERY.md | ☐ |
| 7 | 3개 STEP bounding box 검증 (25.4×25.4×110) | ☐ |
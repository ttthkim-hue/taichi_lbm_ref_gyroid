#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Gyroid Catalyst Support — STL Generator
#
# 목적: SCR 촉매용 Gyroid TPMS 구조의 STL 파일 생성
# 사용법: 아래 파라미터(a, t)만 수정 후 스크립트 실행 → STL 파일이 현재 디렉터리에 저장됨
#
# ---
#
# 도메인 사양
# - 외부: 25.4 × 25.4 × 110 mm (1인치)
# - 외벽: 1.0 mm
# - 내부 유로: 23.4 × 23.4 mm
# - 버퍼: 0-5mm, 105-110mm (Gyroid 없는 빈 유로)
# - 메인: 5-105mm (Gyroid 배치, 100mm)
#
# Gyroid 수식 (Network 타입)
# φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)
# Solid: φ > -t
# Fluid: φ ≤ -t  (Z 방향 관통 보장)
"""

# =============================================================================
# 셀 2: 파라미터 설정 (여기만 수정하세요)
# =============================================================================

# ╔══════════════════════════════════════════╗
# ║  아래 두 숫자만 수정하세요               ║
# ╚══════════════════════════════════════════╝

a = 5.0   # 단위셀 크기 [mm] (3 ~ 8)
t = 0.3   # 두께 파라미터 (0.05 ~ 0.5, 클수록 벽 두꺼움)

# ── 고급 옵션 (보통 수정 불필요) ──
res = 60          # 해상도 (30=빠름/거칠음, 60=기본, 120=고품질/느림)
include_duct = True   # 외벽(1mm) 포함 여부

# ╔══════════════════════════════════════════╗
# ║  수정 후 스크립트 실행                   ║
# ╚══════════════════════════════════════════╝

# 파라미터 검증
a = max(3.0, min(8.0, a))
t = max(0.05, min(0.5, t))
res = max(30, min(120, res))
print(f"✅ 파라미터 확인: a={a} mm, t={t}, 해상도={res}")


# =============================================================================
# 셀 3: 라이브러리 설치 (자동)
# 필요 시: pip install numpy scipy trimesh plotly manifold3d
# =============================================================================


# =============================================================================
# 셀 4: Gyroid 형상 생성
# =============================================================================

import numpy as np
from skimage.measure import marching_cubes
import trimesh
import time
import os

# ── 도메인 상수 ──
DUCT_OUTER = 25.4
WALL = 1.0
DUCT_INNER = DUCT_OUTER - 2 * WALL
TOTAL_Z = 110.0
BUFFER = 5.0
MAIN_START = BUFFER
MAIN_END = TOTAL_Z - BUFFER

print(f"🏗️ 형상 생성 시작... (a={a}, t={t})")
t0 = time.time()

# 1. Gyroid 계산
x_min, x_max = WALL, DUCT_OUTER - WALL
z_min, z_max = MAIN_START, MAIN_END
nx = max(20, int((x_max - x_min) / a * res))
ny = nx
nz = max(20, int((z_max - z_min) / a * res))

x_range = np.linspace(x_min, x_max, nx)
y_range = np.linspace(x_min, x_max, ny)
z_range = np.linspace(z_min, z_max, nz)
X, Y, Z = np.meshgrid(x_range, y_range, z_range, indexing='ij')

k = 2.0 * np.pi / a
phi = (np.sin(k*X) * np.cos(k*Y) + np.sin(k*Y) * np.cos(k*Z) + np.sin(k*Z) * np.cos(k*X))

# 표면 추출
spacing = ((x_max - x_min) / (nx - 1), (x_max - x_min) / (ny - 1), (z_max - z_min) / (nz - 1))
verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=spacing)
verts[:, 0] += x_min
verts[:, 1] += x_min
verts[:, 2] += z_min

gyroid_mesh = trimesh.Trimesh(vertices=verts, faces=faces)

# 2. 외벽(Duct) 생성 및 결합 (필수 수행)
print("🧱 외벽 결합 중 (Manifold Engine 사용)...")
outer_box = trimesh.creation.box(extents=[DUCT_OUTER, DUCT_OUTER, TOTAL_Z])
outer_box.apply_translation([DUCT_OUTER/2, DUCT_OUTER/2, TOTAL_Z/2])
inner_box = trimesh.creation.box(extents=[DUCT_INNER, DUCT_INNER, TOTAL_Z + 2])
inner_box.apply_translation([DUCT_OUTER/2, DUCT_OUTER/2, TOTAL_Z/2])

# manifold 엔진 강제 지정 (설치/재시작 안 했을 시 여기서 에러 발생)
try:
    duct_wall = outer_box.difference(inner_box, engine='manifold')
    combined = trimesh.util.concatenate([gyroid_mesh, duct_wall])
    print("✅ 외벽 결합 성공")
except Exception as e:
    print(f"❌ 오류: 불리언 엔진을 로드할 수 없습니다. manifold3d 설치 후 실행하세요.\n{e}")
    raise

print(f"✨ 완료! (면 수: {len(combined.faces):,}, 소요시간: {time.time()-t0:.1f}초)")


# =============================================================================
# 셀 5: STL 저장
# 실행하면 현재 디렉터리에 STL 파일이 저장됩니다.
# 저장된 STL을 ANSYS SpaceClaim에서 Import하세요.
# =============================================================================

if 'combined' in dir() and combined is not None:
    # 파일명 생성
    a_str = f"{a:.1f}".replace('.', '')
    t_str = f"{t:.2f}"[2:]
    filename = f"gyroid_a{a_str}_t{t_str}.stl"

    # STL 저장
    try:
        combined.export(filename, file_type='stl')
        if os.path.exists(filename):
            abs_path = os.path.abspath(filename)
            print(f"✅ 파일 저장 완료: {filename} ({os.path.getsize(filename)/1024/1024:.1f} MB)")
            print(f"📁 경로: {abs_path}")
        else:
            print("❌ 파일 저장 실패")
    except Exception as e:
        print(f"❌ 내보내기 중 오류 발생: {e}")
else:
    print("❌ 먼저 형상 생성이 완료되어야 합니다.")


# =============================================================================
# ANSYS SpaceClaim Import 안내
#
# 1. File → Open → 저장된 .stl 파일 선택
# 2. 단위 확인: mm 설정
# 3. Facets → Solid 변환: 메쉬 우클릭 → Convert to Solid
# 4. Bounding box 확인: 25.4 × 25.4 × 110 mm
# 5. 유체 영역 추출 후 Fluent/CFX에서 메싱 진행
#
# 수식 참고
# φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)
# Solid: φ > -t
# Fluid: φ ≤ -t  (Network 타입, Z 방향 관통 보장)
#
# 파라미터 가이드
# | 파라미터 | 범위 | 효과 |
# | a (단위셀) | 3~8 mm | 작을수록 촘촘, 표면적↑, 압력손실↑ |
# | t (두께) | 0.05~0.5 | 클수록 벽 두꺼움, 공극률↓ |
# =============================================================================

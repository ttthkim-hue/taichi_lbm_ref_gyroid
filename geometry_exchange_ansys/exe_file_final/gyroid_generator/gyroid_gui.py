#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gyroid Catalyst Support Generator v2
- 복셀 필드 합성 방식: 덕트벽 + 자이로이드를 phi 필드에서 직접 합성
  → mesh boolean 불필요, 단일 marching_cubes로 watertight mesh 생성
- 적응형 Z/XY 레이아웃, 1열 단면 (정면에서 내부 직접 확인)
"""

import gc
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import numpy as np
import trimesh
from skimage.measure import marching_cubes


# ── 고정 규격 (변경 금지) ──
DUCT_OUTER = 25.4          # mm (1인치 정사각)
DUCT_WALL = 1.0            # mm (벽두께)
DUCT_INNER = DUCT_OUTER - 2 * DUCT_WALL  # 23.4mm
TOTAL_Z = 110.0            # mm

# ── 설계 파라미터 ──
WALL_OVERLAP = 0.3          # mm (자이로이드 → 벽 침투)
GYROID_DOMAIN_XY = DUCT_INNER + 2 * WALL_OVERLAP        # 24.0mm
GYROID_XY_START = (DUCT_OUTER - GYROID_DOMAIN_XY) / 2   # 0.7mm
GYROID_XY_END = GYROID_XY_START + GYROID_DOMAIN_XY       # 24.7mm
GYROID_TARGET_Z = 100.0    # mm (자이로이드 목표 길이, buffer ON/OFF 공통)
BUFFER_EACH = 5.0          # mm (앞뒤 버퍼 각각, ON 모드)

# ── 안전 한계 ──
MIN_WALL_THICKNESS = 1.0    # mm (3D 프린팅 최소 벽두께)
MAX_T_SAFE = 0.20           # 위상전이 경고 임계
VOLUME_FRACTION_RANGE = (20.0, 80.0)  # % (극단값 경고)

# ── 메모리 한계 ──
MAX_VOXELS = 150_000_000    # 150M voxels (~600MB float32)

# ── STL 크기 제한 ──
MAX_STL_MB = 12.0
MAX_STL_FACES = int((MAX_STL_MB * 1e6 - 84) / 50)  # binary STL: 84 + 50*N


def _estimate_sa(a: float, n_cells_z: int, total_z: float = TOTAL_Z) -> float:
    """전체 도메인 표면적 추정 (mm²): 자이로이드 + 덕트벽 inner+outer (동적 total_z)."""
    sa_gyroid = 3.1 / a * GYROID_DOMAIN_XY ** 2 * n_cells_z * a
    sa_duct_outer = 4.0 * DUCT_OUTER * total_z
    sa_duct_inner = 4.0 * DUCT_INNER * total_z
    return sa_gyroid + sa_duct_outer + sa_duct_inner


def calc_max_res_for_stl(a: float, n_cells_z: int, total_z: float = TOTAL_Z,
                          max_faces: int = MAX_STL_FACES) -> int:
    """STL max_faces 제한에 맞는 최대 res 계산."""
    sa = _estimate_sa(a, n_cells_z, total_z)
    if sa <= 0:
        return 40
    res_max = (max_faces * a ** 2 / (2.0 * sa)) ** 0.5
    return max(5, int(res_max))


# ── 레이아웃 계산 함수 ──

def calc_z_layout(a: float, use_buffer: bool = True):
    """
    자이로이드 목표 길이는 항상 100mm (a의 정수배, 중앙정렬).

    use_buffer=True (ON):
        총 길이 = 110mm. 자이로이드 구간 = [buffer, buffer+L]. 앞뒤 빈 덕트.
    use_buffer=False (OFF):
        총 길이 = L_gyroid. 자이로이드 구간 = [0, L]. 빈 덕트 없음, 외벽도 L에 맞춤.
    """
    n_cells_z = int(GYROID_TARGET_Z // a)  # floor(100 / a)
    gyroid_z = n_cells_z * a
    remainder = GYROID_TARGET_Z - gyroid_z  # 중앙정렬용 나머지

    if use_buffer:
        total_z = TOTAL_Z  # 110mm
        buffer_each = BUFFER_EACH + remainder / 2.0
        z_start = buffer_each
        z_end = buffer_each + gyroid_z
    else:
        total_z = gyroid_z  # L_gyroid만 (버퍼 없음)
        z_start = 0.0
        z_end = gyroid_z
        buffer_each = 0.0

    return {
        "gyroid_z": gyroid_z,
        "n_cells_z": n_cells_z,
        "duct_front": buffer_each,
        "duct_back": buffer_each,
        "z_start": z_start,
        "z_end": z_end,
        "total_z": total_z,
    }


def calc_xy_layout(a: float):
    """XY 도메인 정합성 계산."""
    n_cells_xy_f = GYROID_DOMAIN_XY / a
    is_integer = abs(n_cells_xy_f - round(n_cells_xy_f)) < 0.01
    suggested = a

    if is_integer:
        n_cells_xy = round(n_cells_xy_f)
        status = "perfect"
    else:
        n_floor = int(n_cells_xy_f)
        n_ceil = n_floor + 1
        a_floor = GYROID_DOMAIN_XY / n_floor
        a_ceil = GYROID_DOMAIN_XY / n_ceil
        suggested = a_floor if abs(a - a_floor) < abs(a - a_ceil) else a_ceil
        n_cells_xy = int(n_cells_xy_f)
        status = "truncated"

    return {
        "n_cells_xy": n_cells_xy,
        "gyroid_start": GYROID_XY_START,
        "gyroid_end": GYROID_XY_END,
        "domain_xy": GYROID_DOMAIN_XY,
        "status": status,
        "suggested_a": suggested,
    }


def calc_full_layout(a: float, use_buffer: bool = True):
    """XY + Z 통합 레이아웃 계산."""
    xy = calc_xy_layout(a)
    z = calc_z_layout(a, use_buffer=use_buffer)
    return {
        **xy, **z,
        "a": a,
        "total_cells": xy["n_cells_xy"] ** 2 * z["n_cells_z"],
    }


class GyroidApp:
    """Gyroid STL/STEP 생성 GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Gyroid Catalyst Support Generator v2")
        self.root.geometry("640x1020")
        self.root.resizable(False, False)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.ui_queue: queue.Queue[tuple] = queue.Queue()
        self.output_dir = os.getcwd()

        self.a_var = tk.DoubleVar(value=4.0)
        self.t_var = tk.DoubleVar(value=0.10)
        self.res_var = tk.IntVar(value=40)
        self.duct_var = tk.BooleanVar(value=True)
        self.buffer_var = tk.BooleanVar(value=True)
        self.stl_var = tk.BooleanVar(value=True)
        self.step_asm_var = tk.BooleanVar(value=True)
        self.step_asm_res_var = tk.IntVar(value=10)
        self.unit_cell_var = tk.BooleanVar(value=False)
        self.cross_section_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._update_info_panel()
        self.root.after(50, self._tick_main_thread)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # ── 파라미터 설정 ──
        param_frame = ttk.LabelFrame(main, text="  파라미터 설정  ", padding=10)
        param_frame.pack(fill="x", padx=4, pady=4)
        param_frame.columnconfigure(1, weight=1)

        ttk.Label(param_frame, text="단위셀 크기 a [mm]:").grid(row=0, column=0, sticky="w")
        a_entry = ttk.Entry(param_frame, textvariable=self.a_var, width=12)
        a_entry.grid(row=0, column=1, sticky="w")
        a_entry.bind("<FocusOut>", lambda e: self._update_info_panel())
        a_entry.bind("<Return>", lambda e: self._update_info_panel())
        ttk.Label(param_frame,
                  text="정합: 4, 6, 8, 12, 24 mm | ANSYS: 10MB대 (STL) | 최대: 30mm",
                  foreground="gray").grid(row=1, column=0, columnspan=2, sticky="w")

        ttk.Label(param_frame, text="두께 파라미터 t:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        t_entry = ttk.Entry(param_frame, textvariable=self.t_var, width=12)
        t_entry.grid(row=2, column=1, sticky="w", pady=(8, 0))
        t_entry.bind("<FocusOut>", lambda e: self._update_info_panel())
        t_entry.bind("<Return>", lambda e: self._update_info_panel())
        ttk.Label(param_frame, text="범위: 0.02~0.20 (0.20 초과: 위상전이, 프린팅 불가)", foreground="gray").grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="STL 해상도 (res):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        res_entry = ttk.Entry(param_frame, textvariable=self.res_var, width=12)
        res_entry.grid(row=4, column=1, sticky="w", pady=(8, 0))
        res_entry.bind("<FocusOut>", lambda e: self._update_info_panel())
        res_entry.bind("<Return>", lambda e: self._update_info_panel())
        ttk.Label(param_frame, text="20=빠름, 40=기본, 120=고품질 (10MB대 자동 조절)",
                  foreground="gray").grid(row=5, column=0, columnspan=2, sticky="w")

        ttk.Checkbutton(param_frame, text="외벽 포함 (1.0mm 덕트벽)", variable=self.duct_var).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        buf_cb = ttk.Checkbutton(param_frame, text="앞뒤 빈 덕트 버퍼 (OFF: 자이로이드 Z 최대화)",
                                  variable=self.buffer_var)
        buf_cb.grid(row=7, column=0, columnspan=2, sticky="w")
        buf_cb.bind("<ButtonRelease-1>", lambda e: self.root.after(50, self._update_info_panel))

        # ── 정보 패널 (레이아웃 + 물성) ──
        info_frame = ttk.LabelFrame(main, text="  레이아웃 / 물성 정보  ", padding=8)
        info_frame.pack(fill="x", padx=4, pady=4)
        self.info_text = tk.Text(info_frame, height=11, font=("Consolas", 9),
                                 state="disabled", bg="#f8f8f8", relief="flat")
        self.info_text.pack(fill="x")

        self.warn_label = ttk.Label(info_frame, text="", foreground="red",
                                    font=("TkDefaultFont", 9, "bold"), wraplength=580)
        self.warn_label.pack(anchor="w", pady=(2, 0))

        # ── 출력 설정 ──
        out_frame = ttk.LabelFrame(main, text="  출력 설정  ", padding=10)
        out_frame.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(out_frame, text="STL 저장 (10MB대 자동 해상도 조절 + 50% decimation)",
                         variable=self.stl_var).pack(anchor="w")

        # STEP 생성 (Assembly)
        step_row = ttk.Frame(out_frame)
        step_row.pack(anchor="w", fill="x")
        ttk.Checkbutton(
            step_row,
            text="STEP 생성 (ISO AP214 Assembly)",
            variable=self.step_asm_var,
        ).pack(side="left")
        ttk.Label(step_row, text="  cell res:").pack(side="left")
        asm_res_entry = ttk.Entry(step_row, textvariable=self.step_asm_res_var, width=5)
        asm_res_entry.pack(side="left")
        asm_res_entry.bind("<FocusOut>", lambda e: self._update_info_panel())
        asm_res_entry.bind("<Return>", lambda e: self._update_info_panel())
        ttk.Label(step_row, text="(8~40)", foreground="gray").pack(side="left")

        ttk.Label(
            out_frame,
            text="  * 단위셀 1회 정의 + N회 인스턴싱 (ANSYS SpaceClaim 호환)",
            foreground="gray",
            font=("TkDefaultFont", 8),
        ).pack(anchor="w")

        ttk.Checkbutton(out_frame, text="단위셀 STL (1 cell, 외벽 없음)", variable=self.unit_cell_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="단면 STL (Y축 2분할, 내부 직접 확인)",
                         variable=self.cross_section_var).pack(anchor="w")

        # ── 출력 폴더 ──
        path_frame = ttk.Frame(main)
        path_frame.pack(fill="x", padx=4, pady=(4, 8))
        ttk.Label(path_frame, text="출력 폴더:").pack(side="left")
        self.path_label = ttk.Label(path_frame, text=self.output_dir, foreground="gray")
        self.path_label.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(path_frame, text="변경", command=self._choose_output_dir).pack(side="right")

        self.btn = ttk.Button(main, text="생성 시작", command=self.on_generate)
        self.btn.pack(pady=(4, 8))

        # ── 로그 ──
        log_frame = ttk.LabelFrame(main, text="  상태 로그  ", padding=6)
        log_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.log = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        # ── 수식 가이드 ──
        guide_frame = ttk.LabelFrame(main, text="  수식 / 가이드  ", padding=8)
        guide_frame.pack(fill="x", padx=4, pady=4)
        ttk.Label(
            guide_frame,
            text="phi = sin(2pi*x/a)cos(2pi*y/a) + sin(2pi*y/a)cos(2pi*z/a) + sin(2pi*z/a)cos(2pi*x/a)",
            font=("Consolas", 8),
        ).pack(anchor="w")
        ttk.Label(
            guide_frame,
            text=f"Solid: phi > -t | Duct: {DUCT_OUTER}x{DUCT_OUTER}x{TOTAL_Z}mm | XY gyroid: {GYROID_DOMAIN_XY}mm",
            font=("Consolas", 8),
        ).pack(anchor="w")

    # ── 정보 패널 ──

    def _update_info_panel(self) -> None:
        try:
            a = max(3.0, min(30.0, float(self.a_var.get())))
            t = max(0.01, min(0.50, float(self.t_var.get())))
        except (tk.TclError, ValueError):
            return

        layout = calc_full_layout(a, use_buffer=self.buffer_var.get())
        vol_frac = self._quick_volume_fraction(a, t)
        wall_t = self._calc_min_wall(a, t, grid_n=40)

        # ── STL 크기 추정 + 10MB대 자동 조절 ──
        try:
            res_input = max(5, min(120, int(self.res_var.get())))
        except (tk.TclError, ValueError):
            res_input = 60
        res_cap = calc_max_res_for_stl(a, layout["n_cells_z"], layout["total_z"])
        res_eff = min(res_input, res_cap)  # 10MB 초과 시 자동 낮춤

        sa_total = _estimate_sa(a, layout["n_cells_z"])
        tri_eff = sa_total * 2.0 / (a / res_eff) ** 2
        stl_mb = (tri_eff * 50 + 84) / 1e6

        if res_eff < res_input:
            stl_line = f"STL: ~{stl_mb:.1f} MB (res {res_input}->{res_eff}, 10MB cap+decimate)"
        else:
            stl_line = f"STL: ~{stl_mb:.1f} MB (res={res_eff}) [OK]"

        # ── STEP Assembly 크기 추정 ──
        try:
            asm_res = max(8, min(40, int(self.step_asm_res_var.get())))
        except (tk.TclError, ValueError):
            asm_res = 25
        n_inst = layout["total_cells"]
        cell_faces_est = 8.0 * asm_res ** 2
        step_geo_kb = cell_faces_est * 1.5
        step_inst_kb = n_inst * 2.0
        step_kb = step_geo_kb + step_inst_kb
        step_line = f"STEP: ~{step_kb:.0f} KB (cell={asm_res}, {n_inst} inst)"

        xy_mark = "[OK]" if layout["status"] == "perfect" else "[!]"

        buf_str = f"buffer {layout['duct_front']:.1f}mm" if self.buffer_var.get() else "no buffer"
        lines = [
            f"--- Layout (a={a:.1f}mm, total_z={layout['total_z']:.1f}mm) ---",
            f"XY: {layout['domain_xy']:.1f}mm ({layout['n_cells_xy']} cells) {xy_mark}"
            f"  |  Z: {layout['gyroid_z']:.1f}mm ({layout['n_cells_z']} cells)",
            f"Z range: [{layout['z_start']:.1f}, {layout['z_end']:.1f}]mm"
            f"  |  {buf_str}",
            f"",
            f"--- Properties (t={t:.2f}) ---",
            f"Volume fraction: {vol_frac:.1f}%",
            f"Min wall: {wall_t:.2f}mm  "
            f"{'[OK >= 1mm]' if wall_t >= MIN_WALL_THICKNESS else '[WARNING < 1mm]'}",
            f"",
            f"--- File Size ---",
            stl_line,
            step_line,
        ]

        if layout["status"] == "truncated":
            lines.append(f"-> Suggested a = {layout['suggested_a']:.1f}mm (perfect fit)")

        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.config(state="disabled")

        warnings = []
        if t > MAX_T_SAFE:
            warnings.append(f"[!] t={t:.2f} > {MAX_T_SAFE}: 위상전이 구간")
        if wall_t < MIN_WALL_THICKNESS:
            warnings.append(f"[!] 벽두께 {wall_t:.2f}mm < {MIN_WALL_THICKNESS}mm")
        if layout["status"] == "truncated":
            warnings.append(f"[i] a={a}mm 비정합")
        if step_kb > 1000:
            warnings.append(f"[i] STEP {step_kb:.0f}KB: cell res 낮추거나 a 증가 권장")

        self.warn_label.config(text="  |  ".join(warnings) if warnings else "")

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="출력 폴더 선택", initialdir=self.output_dir)
        if selected:
            self.output_dir = selected
            self.path_label.config(text=self.output_dir)

    def _append_log(self, msg: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _tick_main_thread(self) -> None:
        try:
            while True:
                cmd = self.ui_queue.get_nowait()
                if cmd[0] == "btn":
                    self._set_button_state(cmd[1])
        except queue.Empty:
            pass
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.root.after(50, self._tick_main_thread)

    def log_msg(self, msg: str) -> None:
        self.log_queue.put(msg)

    def _ui_btn(self, enabled: bool) -> None:
        self.ui_queue.put(("btn", enabled))

    def _set_button_state(self, enabled: bool) -> None:
        self.btn.config(state=("normal" if enabled else "disabled"))

    # ── 벽두께 / 체적분율 ──

    @staticmethod
    def _calc_min_wall(a: float, t: float, grid_n: int = 100) -> float:
        """Local max 방식으로 최소 벽두께 측정 (mm). 2x2x2 타일링."""
        from scipy.ndimage import distance_transform_edt, maximum_filter

        voxel = a / grid_n
        n2 = grid_n * 2
        lin = np.linspace(0, 2 * a, n2, endpoint=False) + voxel / 2
        x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
        k = 2.0 * np.pi / a
        phi = (
            np.sin(k * x) * np.cos(k * y)
            + np.sin(k * y) * np.cos(k * z)
            + np.sin(k * z) * np.cos(k * x)
        )
        solid = phi > -t
        if not solid.any() or solid.all():
            return 0.0
        dt = distance_transform_edt(solid) * voxel
        m = grid_n // 4
        dt_c = dt[m:-m, m:-m, m:-m]
        solid_c = solid[m:-m, m:-m, m:-m]
        if not solid_c.any():
            return 0.0
        lm = maximum_filter(dt_c, size=3)
        ridge = (dt_c == lm) & solid_c & (dt_c > voxel * 1.5)
        if not ridge.any():
            return float(dt_c[solid_c].max()) * 2
        return float(dt_c[ridge].min()) * 2

    def _decimate(self, mesh: "trimesh.Trimesh", ratio: float = 0.5) -> "trimesh.Trimesh":
        """Quadric decimation으로 face 수를 ratio만큼 감소. 실패 시 원본 반환."""
        target = max(100, int(len(mesh.faces) * ratio))
        if len(mesh.faces) <= target:
            return mesh
        try:
            reduced = mesh.simplify_quadric_decimation(target)
            if len(reduced.faces) > 0:
                return reduced
        except Exception as e:
            self.log_msg(f"   [decimation skipped: {e}]")
        return mesh

    @staticmethod
    def _quick_volume_fraction(a: float, t: float, grid_n: int = 50) -> float:
        """저해상도 그리드로 빠른 체적분율 계산."""
        lin = np.linspace(0, a, grid_n, endpoint=False)
        x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
        k = 2.0 * np.pi / a
        phi = (
            np.sin(k * x) * np.cos(k * y)
            + np.sin(k * y) * np.cos(k * z)
            + np.sin(k * z) * np.cos(k * x)
        )
        solid = phi > -t
        return float(solid.sum()) / solid.size * 100

    def on_generate(self) -> None:
        any_output = (self.stl_var.get() or self.step_asm_var.get()
                      or self.unit_cell_var.get() or self.cross_section_var.get())
        if not any_output:
            messagebox.showwarning("출력 선택 필요", "최소 1개 출력 옵션을 선택하세요.")
            return

        try:
            t = float(self.t_var.get())
        except (tk.TclError, ValueError):
            t = 0.10
        if t > MAX_T_SAFE:
            if not messagebox.askyesno(
                "위상전이 경고",
                f"t = {t:.2f}은 {MAX_T_SAFE}을 초과합니다.\n"
                f"얇은 막이 생성되어 3D 프린팅이 불가합니다.\n\n"
                f"그래도 진행하시겠습니까?",
            ):
                return

        self._set_button_state(False)
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self) -> None:
        try:
            self.do_generate()
        except Exception as exc:
            self.log_msg(f"오류: {exc}")
            import traceback
            self.log_msg(traceback.format_exc())
        finally:
            self._ui_btn(True)

    # ── 자이로이드 메시 생성 (복셀 필드 합성) ──

    def _build_gyroid(self, a: float, t: float, res: int,
                      include_duct: bool, z_min: float, z_max: float,
                      total_z: float = TOTAL_Z) -> "trimesh.Trimesh":
        """
        복셀 필드 합성 방식으로 자이로이드(+덕트벽) mesh 생성.
        total_z: 실제 덕트 총 길이 (buffer ON=110, OFF=L_gyroid)
        """
        voxel = a / max(res, 1)

        if include_duct:
            pad = voxel * 2
            x_lo, x_hi = -pad, DUCT_OUTER + pad
            z_lo, z_hi = -pad, total_z + pad
        else:
            # 자이로이드 도메인만
            pad = 0.0
            x_lo, x_hi = GYROID_XY_START, GYROID_XY_END
            z_lo, z_hi = z_min, z_max

        nx = max(20, round((x_hi - x_lo) / voxel))
        ny = nx
        nz = max(20, round((z_hi - z_lo) / voxel))

        # 메모리 보호
        total_vox = nx * ny * nz
        if total_vox > MAX_VOXELS:
            scale = (MAX_VOXELS / total_vox) ** (1.0 / 3.0)
            nx = max(20, int(nx * scale))
            ny = nx
            nz = max(20, int(nz * scale))
            total_vox = nx * ny * nz
            self.log_msg(f"   [!] grid -> {nx}x{ny}x{nz} ({total_vox / 1e6:.1f}M, memory limit)")

        self.log_msg(f"   Grid: {nx}x{ny}x{nz} = {total_vox / 1e6:.1f}M voxels")

        # phi 계산 (broadcasting, float32 절약)
        x = np.linspace(x_lo, x_hi, nx, dtype=np.float32)
        y = np.linspace(x_lo, x_hi, ny, dtype=np.float32)
        z = np.linspace(z_lo, z_hi, nz, dtype=np.float32)

        k = np.float32(2.0 * np.pi / a)
        sx = np.sin(k * x)
        cx = np.cos(k * x)
        sy = np.sin(k * y)
        cy = np.cos(k * y)
        sz = np.sin(k * z)
        cz = np.cos(k * z)

        # phi[i,j,k] = sx[i]*cy[j] + sy[j]*cz[k] + sz[k]*cx[i]
        phi = np.empty((nx, ny, nz), dtype=np.float32)
        phi[:] = sx[:, None, None] * cy[None, :, None]
        phi += sy[None, :, None] * cz[None, None, :]
        phi += sz[None, None, :] * cx[:, None, None]

        if include_duct:
            FORCE_SOLID = np.float32(10.0)
            FORCE_VOID = np.float32(-10.0)

            # 인덱스 경계 계산
            ix_duct_lo = int(np.searchsorted(x, 0.0))
            ix_duct_hi = int(np.searchsorted(x, DUCT_OUTER, side="right"))
            ix_wall_lo = int(np.searchsorted(x, DUCT_WALL))
            ix_wall_hi = int(np.searchsorted(x, DUCT_OUTER - DUCT_WALL, side="right"))

            iy_duct_lo = int(np.searchsorted(y, 0.0))
            iy_duct_hi = int(np.searchsorted(y, DUCT_OUTER, side="right"))
            iy_wall_lo = int(np.searchsorted(y, DUCT_WALL))
            iy_wall_hi = int(np.searchsorted(y, DUCT_OUTER - DUCT_WALL, side="right"))

            iz_duct_lo = int(np.searchsorted(z, 0.0))
            iz_duct_hi = int(np.searchsorted(z, total_z, side="right"))
            iz_gyr_lo = int(np.searchsorted(z, z_min))
            iz_gyr_hi = int(np.searchsorted(z, z_max, side="right"))

            # 1) 덕트 밖 → void
            phi[:ix_duct_lo, :, :] = FORCE_VOID
            phi[ix_duct_hi:, :, :] = FORCE_VOID
            phi[:, :iy_duct_lo, :] = FORCE_VOID
            phi[:, iy_duct_hi:, :] = FORCE_VOID
            phi[:, :, :iz_duct_lo] = FORCE_VOID
            phi[:, :, iz_duct_hi:] = FORCE_VOID

            # 2) 덕트벽 (4면) → solid
            ds = slice(iz_duct_lo, iz_duct_hi)
            phi[ix_duct_lo:ix_wall_lo, iy_duct_lo:iy_duct_hi, ds] = FORCE_SOLID  # 좌벽
            phi[ix_wall_hi:ix_duct_hi, iy_duct_lo:iy_duct_hi, ds] = FORCE_SOLID  # 우벽
            phi[ix_duct_lo:ix_duct_hi, iy_duct_lo:iy_wall_lo, ds] = FORCE_SOLID  # 전벽
            phi[ix_duct_lo:ix_duct_hi, iy_wall_hi:iy_duct_hi, ds] = FORCE_SOLID  # 후벽

            # 3) 앞뒤 버퍼 (내부, 자이로이드 Z 밖) → void
            inner_x = slice(ix_wall_lo, ix_wall_hi)
            inner_y = slice(iy_wall_lo, iy_wall_hi)
            phi[inner_x, inner_y, iz_duct_lo:iz_gyr_lo] = FORCE_VOID  # 전면 버퍼
            phi[inner_x, inner_y, iz_gyr_hi:iz_duct_hi] = FORCE_VOID  # 후면 버퍼

            # 4) 자이로이드 영역은 자연 phi 유지 (수정 없음)
            self.log_msg("   Duct + gyroid field merged (no boolean union)")

        spacing = (
            (x_hi - x_lo) / max(nx - 1, 1),
            (x_hi - x_lo) / max(ny - 1, 1),
            (z_hi - z_lo) / max(nz - 1, 1),
        )

        verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=spacing)
        verts[:, 0] += x_lo
        verts[:, 1] += x_lo
        verts[:, 2] += z_lo

        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        mesh.merge_vertices()
        trimesh.repair.fix_normals(mesh)

        del phi
        gc.collect()
        return mesh

    def _build_unit_cell(self, a: float, t: float, res: int) -> "trimesh.Trimesh":
        """단위셀 1개 (a x a x a mm). 외벽 없음."""
        n = max(20, int(res))
        lin = np.linspace(0, a, n)
        x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
        k = 2.0 * np.pi / a
        phi = (
            np.sin(k * x) * np.cos(k * y)
            + np.sin(k * y) * np.cos(k * z)
            + np.sin(k * z) * np.cos(k * x)
        )
        spacing = (a / max(n - 1, 1),) * 3
        verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=spacing)
        return trimesh.Trimesh(vertices=verts, faces=faces)

    def _build_cross_section(self, mesh: "trimesh.Trimesh", gap_mm: float = 5.0) -> "trimesh.Trimesh":
        """
        Y축 중심 2분할, 양쪽 절단면이 모두 정면(-Y)을 향하도록 배치.

        half_back (y > cy): 절단면 캡 법선이 -Y → 정면에서 바로 내부 보임
        half_front(y < cy): Y축 미러 → 절단면 캡 법선도 -Y로 전환
        두 반쪽을 X방향으로 나란히 배치 (1열 / 서로 가리지 않음)
        """
        bounds = mesh.bounds
        cy = (bounds[0][1] + bounds[1][1]) / 2
        x_size = bounds[1][0] - bounds[0][0]  # 배치 간격 계산용

        try:
            # half_back: y >= cy 쪽, 절단 캡 법선 = -Y (정면을 향함)
            half_back = mesh.slice_plane([0, cy, 0], [0, 1, 0], cap=True)
            # half_front: y <= cy 쪽, 절단 캡 법선 = +Y (정면 반대) → 미러로 반전
            half_front = mesh.slice_plane([0, cy, 0], [0, -1, 0], cap=True)
        except Exception as e:
            self.log_msg(f"   단면 분할 실패: {e}")
            return mesh

        # half_front를 Y 미러 → 절단면 법선이 -Y로 전환 (정면을 향함)
        half_front.vertices[:, 1] = 2 * cy - half_front.vertices[:, 1]
        half_front.invert()  # 홀수축 미러 → 법선 방향 보정

        # X방향으로 나란히 배치 (gap 간격), 양쪽 모두 절단면이 -Y 정면을 향함
        half_back.apply_translation([-(x_size / 2 + gap_mm), 0, 0])
        half_front.apply_translation([+(gap_mm), 0, 0])

        parts = [p for p in [half_back, half_front] if len(p.faces) > 0]
        if not parts:
            self.log_msg("   단면 결과 비어있음")
            return mesh
        return trimesh.util.concatenate(parts)

    # ── STEP 변환 (Assembly) ──

    @staticmethod
    def _find_asm_converter() -> str:
        """step_converter_assembly 실행 파일/스크립트 경로 탐색."""
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
            for name in ("step_converter_assembly.exe", "step_converter_assembly"):
                p = os.path.join(base, name)
                if os.path.isfile(p):
                    return p
            p = os.path.join(base, "_internal", "step_converter_assembly.py")
            if os.path.isfile(p):
                return p
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step_converter_assembly.py")
        if os.path.isfile(p):
            return p
        return ""

    def convert_to_step_assembly(self, a: float, t: float, res_cell: int,
                                  layout: dict, include_duct: bool,
                                  step_path: str) -> bool:
        """
        step_converter_assembly를 서브프로세스로 실행.
        ISO 10303-214 Assembly STEP 생성 (단위셀 인스턴싱 방식).
        """
        converter = self._find_asm_converter()
        if not converter:
            self.log_msg("   step_converter_assembly를 찾을 수 없음")
            return False

        step_abs = str(Path(step_path).resolve())
        n_xy = layout["n_cells_xy"]
        n_z  = layout["n_cells_z"]
        z_start = layout["z_start"]
        l_total_z = layout["total_z"]
        duct_flag = "1" if include_duct else "0"

        args = [str(a), str(t), str(res_cell),
                str(n_xy), str(n_z), str(z_start),
                str(GYROID_XY_START), duct_flag, str(l_total_z), step_abs]

        if converter.endswith(".py"):
            cmd = [sys.executable, converter] + args
        else:
            cmd = [converter] + args

        self.log_msg(f"   Assembly STEP start...")
        self.log_msg(f"   CMD: {os.path.basename(converter)}")

        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                if line:
                    self.log_msg(f"   {line}")
            proc.wait()
            if proc.returncode == 0:
                if os.path.isfile(step_abs):
                    size_kb = os.path.getsize(step_abs) / 1024
                    self.log_msg(f"   Assembly STEP 저장 완료 ({size_kb:.1f} KB)")
                return True
            else:
                self.log_msg(f"   Assembly STEP 변환 실패 (exit code {proc.returncode})")
                return False
        except Exception as exc:
            self.log_msg(f"   Assembly STEP 프로세스 오류: {exc}")
            return False

    # ── 메인 생성 흐름 ──

    def do_generate(self) -> None:
        a = max(3.0, min(30.0, float(self.a_var.get())))
        t = max(0.01, min(0.50, float(self.t_var.get())))
        res_input = max(5, min(120, int(self.res_var.get())))
        include_duct = bool(self.duct_var.get())
        use_buffer = bool(self.buffer_var.get())

        layout = calc_full_layout(a, use_buffer=use_buffer)
        z_min = layout["z_start"]
        z_max = layout["z_end"]
        dyn_total_z = layout["total_z"]  # 동적 total_z (ON=110, OFF=L_gyroid)

        wall_t = self._calc_min_wall(a, t)
        vol_frac = self._quick_volume_fraction(a, t)

        # ── STL 10MB대 자동 해상도 조절 ──
        res_cap = calc_max_res_for_stl(a, layout["n_cells_z"], layout["total_z"])
        res = min(res_input, res_cap)
        if res < res_input:
            self.log_msg(f"[!] STL ~10MB cap: res {res_input} -> {res}")

        self.log_msg(f"=== Gyroid Generator v4 ===")
        self.log_msg(f"Parameters: a={a:.1f}mm, t={t:.2f}, duct={include_duct}")
        self.log_msg(f"Buffer: {'ON' if use_buffer else 'OFF'} | "
                      f"total_z={dyn_total_z:.1f}mm | gyroid={layout['gyroid_z']:.1f}mm")
        self.log_msg(f"Layout: XY=[{layout['gyroid_start']:.1f}, {layout['gyroid_end']:.1f}]mm "
                      f"({layout['n_cells_xy']} cells, {layout['status']})")
        self.log_msg(f"Layout: Z=[{z_min:.1f}, {z_max:.1f}]mm "
                      f"({layout['n_cells_z']} cells)")
        self.log_msg(f"STL res={res} (input={res_input}, cap={res_cap})")
        self.log_msg(f"Volume fraction: {vol_frac:.1f}%")
        self.log_msg(f"Min wall thickness: {wall_t:.2f}mm")

        if wall_t < MIN_WALL_THICKNESS:
            self.log_msg(f"[!] wall {wall_t:.2f}mm < {MIN_WALL_THICKNESS}mm (not printable)")
        if t > MAX_T_SAFE:
            self.log_msg(f"[!] t={t:.2f} > {MAX_T_SAFE} (topology transition)")
        if layout["status"] == "truncated":
            self.log_msg(f"[i] a={a} not aligned. Suggested: {layout['suggested_a']:.1f}mm")

        a_str = f"{a:.1f}".replace(".", "")
        t_str = f"{t:.2f}"[2:]
        base_name = f"gyroid_a{a_str}_t{t_str}"

        stl_path = os.path.join(self.output_dir, f"{base_name}.stl")

        # ── STL ──
        if self.stl_var.get():
            self.log_msg(f"[STL] Mesh build (res={res})...")
            t0 = time.time()
            stl_mesh = self._build_gyroid(a, t, res, include_duct, z_min, z_max, dyn_total_z)
            n_orig = len(stl_mesh.faces)
            elapsed = time.time() - t0
            self.log_msg(f"[STL] {n_orig:,} faces ({elapsed:.1f}s)")

            # 50% decimation
            stl_mesh = self._decimate(stl_mesh, ratio=0.5)
            self.log_msg(f"[STL] decimated: {len(stl_mesh.faces):,} faces")

            stl_mesh.export(stl_path, file_type="stl")
            stl_size = os.path.getsize(stl_path) / 1024 / 1024
            self.log_msg(f"[STL] saved: {stl_path} ({stl_size:.1f} MB)")
            del stl_mesh
            gc.collect()

        # ── 단위셀 ──
        if self.unit_cell_var.get():
            self.log_msg(f"[단위셀] 생성 중 (a={a:.1f}mm, res={res})...")
            t0 = time.time()
            uc_mesh = self._build_unit_cell(a, t, res)
            elapsed = time.time() - t0
            uc_path = os.path.join(self.output_dir, f"{base_name}_unitcell.stl")
            uc_mesh.export(uc_path, file_type="stl")
            uc_size = os.path.getsize(uc_path) / 1024 / 1024
            self.log_msg(f"[단위셀] 완료 ({len(uc_mesh.faces):,} faces, {elapsed:.1f}s, {uc_size:.1f} MB)")
            del uc_mesh
            gc.collect()

        # ── 단면 (Y축 2분할, 절단면 정면 배치) ──
        if self.cross_section_var.get():
            self.log_msg(f"[cross-section] build (res={res})...")
            t0 = time.time()
            cs_mesh = self._build_gyroid(a, t, res, include_duct, z_min, z_max, dyn_total_z)
            cs_mesh = self._build_cross_section(cs_mesh, gap_mm=5.0)
            cs_mesh = self._decimate(cs_mesh, ratio=0.5)
            elapsed = time.time() - t0
            cs_path = os.path.join(self.output_dir, f"{base_name}_cross_section.stl")
            cs_mesh.export(cs_path, file_type="stl")
            cs_size = os.path.getsize(cs_path) / 1024 / 1024
            self.log_msg(f"[cross-section] {len(cs_mesh.faces):,} faces, {elapsed:.1f}s, {cs_size:.1f} MB")
            del cs_mesh
            gc.collect()

        # ── STEP (ISO AP214 Assembly) ──
        if self.step_asm_var.get():
            try:
                res_cell = max(8, min(40, int(self.step_asm_res_var.get())))
            except (tk.TclError, ValueError):
                res_cell = 25
            step_path = os.path.join(self.output_dir, f"{base_name}.step")
            n_inst = layout["n_cells_xy"] ** 2 * layout["n_cells_z"]
            self.log_msg(f"[STEP] Assembly STEP 생성 (cell res={res_cell}, "
                         f"{layout['n_cells_xy']}x{layout['n_cells_xy']}x{layout['n_cells_z']}="
                         f"{n_inst} instances)...")
            self.convert_to_step_assembly(a, t, res_cell, layout, include_duct, step_path)

        self.log_msg("=== 완료! ===")


if __name__ == "__main__":
    root = tk.Tk()
    app = GyroidApp(root)
    root.mainloop()

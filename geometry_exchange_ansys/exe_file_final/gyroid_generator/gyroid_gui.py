#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
WALL_OVERLAP = 0.3          # mm (자이로이드→벽 침투)
GYROID_DOMAIN_XY = DUCT_INNER + 2 * WALL_OVERLAP        # 24.0mm
GYROID_XY_START = (DUCT_OUTER - GYROID_DOMAIN_XY) / 2   # 0.7mm
GYROID_XY_END = GYROID_XY_START + GYROID_DOMAIN_XY       # 24.7mm
MIN_DUCT_Z = 5.0           # mm (앞뒤 최소 빈 덕트)
MIN_DUCT_Z_FALLBACK = 4.0  # mm (차선)

# ── 안전 한계 ──
MIN_WALL_THICKNESS = 1.0    # mm (3D 프린팅 최소 벽두께)
MAX_T_SAFE = 0.20           # 위상전이 경고 임계
VOLUME_FRACTION_RANGE = (20.0, 80.0)  # % (극단값 경고)


# ── 레이아웃 계산 함수 (모듈 레벨) ──

def calc_z_layout(a: float, total_z: float = TOTAL_Z, min_duct: float = MIN_DUCT_Z):
    """
    Z=110mm 고정, 앞뒤 최소 5mm(안되면 4mm) 빈 덕트 확보.
    자이로이드 Z 길이는 a의 최대 정수배.
    """
    max_gyroid_z = total_z - 2 * min_duct      # 100mm
    n_cells_z = int(max_gyroid_z // a)
    gyroid_z = n_cells_z * a
    remainder = total_z - gyroid_z

    # 앞뒤 5mm 이상 확보 실패 시 → 4mm로 재시도
    if remainder / 2 < MIN_DUCT_Z_FALLBACK:
        min_duct = MIN_DUCT_Z_FALLBACK
        max_gyroid_z = total_z - 2 * min_duct   # 102mm
        n_cells_z = int(max_gyroid_z // a)
        gyroid_z = n_cells_z * a
        remainder = total_z - gyroid_z

    duct_each = remainder / 2  # 앞뒤 균등 분배

    return {
        "gyroid_z": gyroid_z,
        "n_cells_z": n_cells_z,
        "duct_front": duct_each,
        "duct_back": duct_each,
        "z_start": duct_each,
        "z_end": duct_each + gyroid_z,
    }


def calc_xy_layout(a: float):
    """XY 도메인 정합성 계산"""
    n_cells_xy_f = GYROID_DOMAIN_XY / a
    is_integer = abs(n_cells_xy_f - round(n_cells_xy_f)) < 0.01
    suggested = a

    if is_integer:
        n_cells_xy = round(n_cells_xy_f)
        status = "perfect"
    else:
        n_floor = int(n_cells_xy_f)
        n_ceil = n_floor + 1
        a_floor = GYROID_DOMAIN_XY / n_floor   # 더 큰 a
        a_ceil = GYROID_DOMAIN_XY / n_ceil      # 더 작은 a
        suggested = a_floor if abs(a - a_floor) < abs(a - a_ceil) else a_ceil
        n_cells_xy = int(n_cells_xy_f)          # 잘린 셀 포함
        status = "truncated"

    return {
        "n_cells_xy": n_cells_xy,
        "gyroid_start": GYROID_XY_START,
        "gyroid_end": GYROID_XY_END,
        "domain_xy": GYROID_DOMAIN_XY,
        "status": status,
        "suggested_a": suggested,
    }


def calc_full_layout(a: float):
    """XY + Z 통합 레이아웃 계산"""
    xy = calc_xy_layout(a)
    z = calc_z_layout(a, TOTAL_Z)
    return {
        **xy, **z,
        "a": a,
        "total_cells": xy["n_cells_xy"] ** 2 * z["n_cells_z"],
    }


# ── 3단계 Robust Union ──

def robust_union(duct_wall, gyroid_mesh, log_fn=None):
    """
    3단계 fallback. concatenate는 절대 사용하지 않음.
    Level 1: 직접 union (0.3mm 오버랩 이미 적용된 상태)
    Level 2: 미세 스케일링 후 재시도 (+0.1%)
    Level 3: voxel remesh 후 union
    실패 시: RuntimeError
    """
    if log_fn is None:
        log_fn = print

    # 사전 정리
    for m in [duct_wall, gyroid_mesh]:
        m.update_faces(m.nondegenerate_faces())
        m.merge_vertices()
        m.fix_normals()

    # Level 1: 직접 union
    try:
        result = duct_wall.union(gyroid_mesh, engine="manifold")
        if result is not None and len(result.faces) > 0:
            log_fn("   [Union L1] Direct union OK")
            return result
    except Exception as e:
        log_fn(f"   [Union L1] Failed: {e}")

    # Level 2: 미세 확장 후 재시도
    try:
        g2 = gyroid_mesh.copy()
        c = g2.centroid
        g2.vertices = (g2.vertices - c) * 1.001 + c
        result = duct_wall.union(g2, engine="manifold")
        if result is not None and len(result.faces) > 0:
            log_fn("   [Union L2] Scaled union OK")
            return result
    except Exception as e:
        log_fn(f"   [Union L2] Failed: {e}")

    # Level 3: voxel remesh
    try:
        pitch = 0.08  # mm
        log_fn("   [Union L3] Voxel remesh (pitch=0.08mm)...")
        gv = gyroid_mesh.voxelized(pitch).fill()
        dv = duct_wall.voxelized(pitch).fill()
        combined_mat = gv.matrix | dv.matrix
        from trimesh.voxel import VoxelGrid
        from trimesh.voxel.encoding import DenseEncoding
        vg = VoxelGrid(DenseEncoding(combined_mat), transform=gv.transform)
        result = vg.marching_cubes
        if result is not None and len(result.faces) > 0:
            log_fn("   [Union L3] Voxel union OK")
            return result
    except Exception as e:
        log_fn(f"   [Union L3] Failed: {e}")

    raise RuntimeError(
        "Boolean union failed at all 3 levels.\n"
        "Check mesh quality: degenerate faces, self-intersections."
    )


class GyroidApp:
    """Gyroid STL/STEP 생성 GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Gyroid Catalyst Support - Generator v2")
        self.root.geometry("640x1020")
        self.root.resizable(False, False)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.ui_queue: queue.Queue[tuple] = queue.Queue()
        self.output_dir = os.getcwd()

        self.a_var = tk.DoubleVar(value=4.0)
        self.t_var = tk.DoubleVar(value=0.10)
        self.res_var = tk.IntVar(value=60)
        self.step_res_var = tk.IntVar(value=8)
        self.duct_var = tk.BooleanVar(value=True)
        self.stl_var = tk.BooleanVar(value=True)
        self.step_var = tk.BooleanVar(value=True)
        self.unit_cell_var = tk.BooleanVar(value=False)
        self.cross_section_var = tk.BooleanVar(value=False)
        self.thickness_vis_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._update_info_panel()
        self.root.after(50, self._tick_main_thread)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # ── 파라미터 설정 ──
        param_frame = ttk.LabelFrame(main, text="Parameter Settings", padding=10)
        param_frame.pack(fill="x", padx=4, pady=4)
        param_frame.columnconfigure(1, weight=1)

        ttk.Label(param_frame, text="Unit cell size a [mm]:").grid(row=0, column=0, sticky="w")
        a_entry = ttk.Entry(param_frame, textvariable=self.a_var, width=12)
        a_entry.grid(row=0, column=1, sticky="w")
        a_entry.bind("<FocusOut>", lambda e: self._update_info_panel())
        a_entry.bind("<Return>", lambda e: self._update_info_panel())
        ttk.Label(param_frame, text="Recommended: 3.0 ~ 8.0 mm (best: 4, 6, 8)", foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="Thickness param t:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        t_entry = ttk.Entry(param_frame, textvariable=self.t_var, width=12)
        t_entry.grid(row=2, column=1, sticky="w", pady=(8, 0))
        t_entry.bind("<FocusOut>", lambda e: self._update_info_panel())
        t_entry.bind("<Return>", lambda e: self._update_info_panel())
        ttk.Label(param_frame, text="Range: 0.02~0.20 (t>0.20: topology transition, not printable)", foreground="gray").grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="STL resolution (res):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.res_var, width=12).grid(row=4, column=1, sticky="w", pady=(8, 0))
        ttk.Label(param_frame, text="30=fast, 60=default, 120=high quality (STL only)", foreground="gray").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="STEP resolution:").grid(row=6, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.step_res_var, width=12).grid(row=6, column=1, sticky="w", pady=(8, 0))
        ttk.Label(
            param_frame,
            text="5=fast(~1min), 8=default(~2min), 15=HQ(slow) - STEP only",
            foreground="gray",
        ).grid(row=7, column=0, columnspan=2, sticky="w")

        ttk.Checkbutton(param_frame, text="Include duct wall (1.0mm)", variable=self.duct_var).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        # ── 정보 패널 (레이아웃 + 물성) ──
        info_frame = ttk.LabelFrame(main, text="Layout & Properties", padding=8)
        info_frame.pack(fill="x", padx=4, pady=4)
        self.info_text = tk.Text(info_frame, height=9, font=("Consolas", 9),
                                 state="disabled", bg="#f8f8f8", relief="flat")
        self.info_text.pack(fill="x")

        # 경고 레이블
        self.warn_label = ttk.Label(info_frame, text="", foreground="red",
                                    font=("TkDefaultFont", 9, "bold"), wraplength=580)
        self.warn_label.pack(anchor="w", pady=(2, 0))

        # ── 출력 설정 ──
        out_frame = ttk.LabelFrame(main, text="Output Options", padding=10)
        out_frame.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(out_frame, text="STL export", variable=self.stl_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="STEP export", variable=self.step_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="Unit cell STL (1 cell, no duct)", variable=self.unit_cell_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="Cross-section STL (mirror-flip, interior view)",
                         variable=self.cross_section_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="Wall thickness visualization (dual isosurface, preview only)",
                         variable=self.thickness_vis_var).pack(anchor="w")
        ttk.Label(
            out_frame,
            text="* STEP uses separate low-res mesh (same geometry, faster sewing)",
            foreground="gray",
            font=("TkDefaultFont", 8),
        ).pack(anchor="w", pady=(4, 0))

        # ── 출력 폴더 ──
        path_frame = ttk.Frame(main)
        path_frame.pack(fill="x", padx=4, pady=(4, 8))
        ttk.Label(path_frame, text="Output folder:").pack(side="left")
        self.path_label = ttk.Label(path_frame, text=self.output_dir, foreground="gray")
        self.path_label.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(path_frame, text="Browse", command=self._choose_output_dir).pack(side="right")

        self.btn = ttk.Button(main, text="Generate", command=self.on_generate)
        self.btn.pack(pady=(4, 8))

        # ── 로그 ──
        log_frame = ttk.LabelFrame(main, text="Status Log", padding=6)
        log_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.log = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        # ── 수식 가이드 ──
        guide_frame = ttk.LabelFrame(main, text="Formula / Guide", padding=8)
        guide_frame.pack(fill="x", padx=4, pady=4)
        ttk.Label(
            guide_frame,
            text="phi = sin(2pi*x/a)cos(2pi*y/a) + sin(2pi*y/a)cos(2pi*z/a) + sin(2pi*z/a)cos(2pi*x/a)",
            font=("Consolas", 8),
        ).pack(anchor="w")
        ttk.Label(
            guide_frame,
            text=f"Solid: phi > -t | Domain: {DUCT_OUTER}x{DUCT_OUTER}x{TOTAL_Z}mm | XY gyroid: {GYROID_DOMAIN_XY}mm",
            font=("Consolas", 8),
        ).pack(anchor="w")

    # ── 정보 패널 업데이트 ──

    def _update_info_panel(self) -> None:
        """a, t 변경 시 정보 패널 실시간 업데이트"""
        try:
            a = max(3.0, min(10.0, float(self.a_var.get())))
            t = max(0.01, min(0.50, float(self.t_var.get())))
        except (tk.TclError, ValueError):
            return

        layout = calc_full_layout(a)
        vol_frac = self._quick_volume_fraction(a, t)
        wall_t = self._calc_min_wall(a, t, grid_n=40)  # 저해상도 for UI speed

        xy_status = "OK" if layout["status"] == "perfect" else "TRUNCATED"
        xy_mark = "[OK]" if layout["status"] == "perfect" else "[!]"

        lines = [
            f"--- Layout (a={a:.1f}mm) ---",
            f"XY domain: {layout['domain_xy']:.1f}mm  "
            f"({layout['n_cells_xy']} cells)  {xy_mark}",
            f"Z  domain: {layout['gyroid_z']:.1f}mm  "
            f"({layout['n_cells_z']} cells)",
            f"Front/back duct: {layout['duct_front']:.1f}mm each",
            f"Z range: [{layout['z_start']:.1f}, {layout['z_end']:.1f}]mm",
            f"",
            f"--- Properties (t={t:.2f}) ---",
            f"Volume fraction: {vol_frac:.1f}%",
            f"Min wall thickness: {wall_t:.2f}mm  "
            f"{'[OK >= 1mm]' if wall_t >= MIN_WALL_THICKNESS else '[WARNING < 1mm]'}",
            f"Total cells: ~{layout['total_cells']}",
        ]

        # 비정합 시 추천
        if layout["status"] == "truncated":
            lines.append(f"")
            lines.append(f"-> Suggested a = {layout['suggested_a']:.1f}mm (perfect alignment)")

        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.config(state="disabled")

        # 경고 수집
        warnings = []
        if t > MAX_T_SAFE:
            warnings.append(f"WARNING: t={t:.2f} > {MAX_T_SAFE} - topology transition, thin membranes!")
        if wall_t < MIN_WALL_THICKNESS:
            warnings.append(f"WARNING: wall {wall_t:.2f}mm < {MIN_WALL_THICKNESS}mm - not printable!")
        if layout["status"] == "truncated":
            warnings.append(f"NOTE: a={a} not aligned with XY {GYROID_DOMAIN_XY}mm domain")
        if vol_frac < VOLUME_FRACTION_RANGE[0] or vol_frac > VOLUME_FRACTION_RANGE[1]:
            warnings.append(f"NOTE: volume fraction {vol_frac:.1f}% outside typical range {VOLUME_FRACTION_RANGE}")

        self.warn_label.config(text="  |  ".join(warnings) if warnings else "")

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder", initialdir=self.output_dir)
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

    # ── 벽두께 / 체적분율 계산 ──

    @staticmethod
    def _calc_min_wall(a: float, t: float, grid_n: int = 100) -> float:
        """Local max 방식으로 최소 벽두께 측정 (mm). 2x2x2 타일링으로 주기 경계 처리."""
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

    @staticmethod
    def _quick_volume_fraction(a: float, t: float, grid_n: int = 50) -> float:
        """저해상도 그리드로 빠른 체적분율 계산 (~0.01초)"""
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
        any_output = (self.stl_var.get() or self.step_var.get() or self.unit_cell_var.get()
                      or self.cross_section_var.get() or self.thickness_vis_var.get())
        if not any_output:
            messagebox.showwarning("Output required", "Select at least one output option.")
            return

        # t > MAX_T_SAFE 경고 팝업
        try:
            t = float(self.t_var.get())
        except (tk.TclError, ValueError):
            t = 0.10
        if t > MAX_T_SAFE:
            if not messagebox.askyesno(
                "Topology Warning",
                f"t = {t:.2f} exceeds {MAX_T_SAFE}.\n"
                f"Thin membranes will form (not 3D-printable).\n\n"
                f"Continue anyway?",
            ):
                return

        self._set_button_state(False)
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self) -> None:
        try:
            self.do_generate()
        except Exception as exc:
            self.log_msg(f"Error: {exc}")
            import traceback
            self.log_msg(traceback.format_exc())
        finally:
            self._ui_btn(True)

    # ── 자이로이드 메시 생성 ──

    def _build_gyroid(self, a: float, t: float, res: int,
                      include_duct: bool, z_min: float, z_max: float,
                      dual_isosurface: bool = False) -> "trimesh.Trimesh":
        """주어진 해상도로 자이로이드 메시를 생성하여 반환."""
        x_min, x_max_coord = GYROID_XY_START, GYROID_XY_END
        nx = max(20, int((x_max_coord - x_min) / a * res))
        ny = nx
        nz = max(20, int((z_max - z_min) / a * res))

        x_range = np.linspace(x_min, x_max_coord, nx)
        y_range = np.linspace(x_min, x_max_coord, ny)
        z_range = np.linspace(z_min, z_max, nz)
        x_grid, y_grid, z_grid = np.meshgrid(x_range, y_range, z_range, indexing="ij")

        k = 2.0 * np.pi / a
        phi = (
            np.sin(k * x_grid) * np.cos(k * y_grid)
            + np.sin(k * y_grid) * np.cos(k * z_grid)
            + np.sin(k * z_grid) * np.cos(k * x_grid)
        )

        spacing = (
            (x_max_coord - x_min) / max(nx - 1, 1),
            (x_max_coord - x_min) / max(ny - 1, 1),
            (z_max - z_min) / max(nz - 1, 1),
        )

        # 외부 표면 (phi > -t)
        verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=spacing)
        verts[:, 0] += x_min
        verts[:, 1] += x_min
        verts[:, 2] += z_min
        gyroid_mesh = trimesh.Trimesh(vertices=verts, faces=faces)

        # Dual isosurface (벽두께 시각화용)
        if dual_isosurface:
            try:
                verts_in, faces_in, _, _ = marching_cubes(phi, level=+t, spacing=spacing)
                faces_in = faces_in[:, ::-1]  # 법선 반전
                verts_in[:, 0] += x_min
                verts_in[:, 1] += x_min
                verts_in[:, 2] += z_min
                mesh_in = trimesh.Trimesh(vertices=verts_in, faces=faces_in)
                gyroid_mesh = trimesh.util.concatenate([gyroid_mesh, mesh_in])
                self.log_msg("   Dual isosurface generated (thickness visualization)")
            except Exception as e:
                self.log_msg(f"   Dual isosurface failed: {e}")

        combined = gyroid_mesh

        if include_duct:
            self.log_msg("   Boolean Union (robust 3-level)...")
            outer_box = trimesh.creation.box(extents=[DUCT_OUTER, DUCT_OUTER, TOTAL_Z])
            outer_box.apply_translation([DUCT_OUTER / 2, DUCT_OUTER / 2, TOTAL_Z / 2])
            inner_box = trimesh.creation.box(extents=[DUCT_INNER, DUCT_INNER, TOTAL_Z + 2])
            inner_box.apply_translation([DUCT_OUTER / 2, DUCT_OUTER / 2, TOTAL_Z / 2])
            duct_wall = outer_box.difference(inner_box, engine="manifold")
            try:
                combined = robust_union(duct_wall, gyroid_mesh, log_fn=self.log_msg)
            except RuntimeError as e:
                self.log_msg(f"   ERROR: {e}")
                self.log_msg("   Returning gyroid mesh without duct (union failed)")
                combined = gyroid_mesh

        return combined

    def _build_unit_cell(self, a: float, t: float, res: int) -> "trimesh.Trimesh":
        """단위셀 1개 (a x a x a mm) 자이로이드 메시 생성. 외벽 없음."""
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

    def _build_cross_section(self, mesh: "trimesh.Trimesh", gap_mm: float = 25.0) -> "trimesh.Trimesh":
        """미러 플립 4분할: 절단면이 모두 바깥(카메라 방향)을 향하도록."""
        bounds = mesh.bounds
        cx = (bounds[0][0] + bounds[1][0]) / 2
        cy = (bounds[0][1] + bounds[1][1]) / 2
        half = gap_mm / 2

        try:
            # 분할
            top = mesh.slice_plane([cx, cy, 0], [0, -1, 0], cap=True)
            bottom = mesh.slice_plane([cx, cy, 0], [0, 1, 0], cap=True)
            q1 = top.slice_plane([cx, cy, 0], [-1, 0, 0], cap=True)    # X>cx, Y>cy
            q2 = top.slice_plane([cx, cy, 0], [1, 0, 0], cap=True)     # X<cx, Y>cy
            q3 = bottom.slice_plane([cx, cy, 0], [1, 0, 0], cap=True)  # X<cx, Y<cy
            q4 = bottom.slice_plane([cx, cy, 0], [-1, 0, 0], cap=True) # X>cx, Y<cy
        except Exception as e:
            self.log_msg(f"   Cross-section slicing failed: {e}")
            return mesh

        # Q1: 기준 — 이동만
        q1.apply_translation([+half, +half, 0])

        # Q2: X 미러 → 절단면(+X)이 바깥으로
        q2.vertices[:, 0] = 2 * cx - q2.vertices[:, 0]
        q2.invert()
        q2.apply_translation([-half, +half, 0])

        # Q3: X+Y 미러 (짝수 반사 → invert 불필요)
        q3.vertices[:, 0] = 2 * cx - q3.vertices[:, 0]
        q3.vertices[:, 1] = 2 * cy - q3.vertices[:, 1]
        q3.apply_translation([-half, -half, 0])

        # Q4: Y 미러
        q4.vertices[:, 1] = 2 * cy - q4.vertices[:, 1]
        q4.invert()
        q4.apply_translation([+half, -half, 0])

        parts = [q for q in [q1, q2, q3, q4] if len(q.faces) > 0]
        if not parts:
            self.log_msg("   Cross-section: empty result")
            return mesh
        result = trimesh.util.concatenate(parts)
        result.fix_normals()
        return result

    # ── STEP 변환 ──

    @staticmethod
    def _find_converter() -> str:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
            for name in ("step_converter.exe", "step_converter"):
                p = os.path.join(base, name)
                if os.path.isfile(p):
                    return p
            p = os.path.join(base, "_internal", "step_converter.py")
            if os.path.isfile(p):
                return p
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step_converter.py")
        if os.path.isfile(p):
            return p
        return ""

    def convert_to_step(self, stl_path: str, step_path: str) -> bool:
        converter = self._find_converter()
        if not converter:
            self.log_msg("   step_converter not found")
            return False

        stl_abs = str(Path(stl_path).resolve())
        step_abs = str(Path(step_path).resolve())

        if converter.endswith(".py"):
            cmd = [sys.executable, converter, stl_abs, step_abs]
        else:
            cmd = [converter, stl_abs, step_abs]

        self.log_msg(f"   STEP conversion starting...")
        self.log_msg(f"   CMD: {os.path.basename(converter)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                if line:
                    self.log_msg(f"   {line}")
            proc.wait()
            if proc.returncode == 0:
                if os.path.isfile(step_abs):
                    size_mb = os.path.getsize(step_abs) / 1024 / 1024
                    self.log_msg(f"   STEP saved ({size_mb:.1f} MB)")
                return True
            else:
                self.log_msg(f"   STEP conversion failed (exit code {proc.returncode})")
                return False
        except Exception as exc:
            self.log_msg(f"   STEP process error: {exc}")
            return False

    # ── 메인 생성 흐름 ──

    def do_generate(self) -> None:
        a = max(3.0, min(10.0, float(self.a_var.get())))
        t = max(0.01, min(0.50, float(self.t_var.get())))
        res = max(30, min(120, int(self.res_var.get())))
        step_res = max(3, min(15, int(self.step_res_var.get())))
        include_duct = bool(self.duct_var.get())
        dual_iso = bool(self.thickness_vis_var.get())

        # 적응형 레이아웃 계산
        layout = calc_full_layout(a)
        z_min = layout["z_start"]
        z_max = layout["z_end"]

        # 벽두께 검증
        wall_t = self._calc_min_wall(a, t)
        vol_frac = self._quick_volume_fraction(a, t)

        self.log_msg(f"=== Gyroid Generator v2 ===")
        self.log_msg(f"Parameters: a={a:.1f}mm, t={t:.2f}, duct={include_duct}")
        self.log_msg(f"Layout: XY=[{layout['gyroid_start']:.1f}, {layout['gyroid_end']:.1f}]mm "
                      f"({layout['n_cells_xy']} cells, {layout['status']})")
        self.log_msg(f"Layout: Z=[{z_min:.1f}, {z_max:.1f}]mm "
                      f"({layout['n_cells_z']} cells, {layout['gyroid_z']:.1f}mm)")
        self.log_msg(f"Front/back duct: {layout['duct_front']:.1f}mm each")
        self.log_msg(f"Resolution: STL={res}, STEP={step_res}")
        self.log_msg(f"Volume fraction: {vol_frac:.1f}%")
        self.log_msg(f"Min wall thickness: {wall_t:.2f}mm")

        if wall_t < MIN_WALL_THICKNESS:
            self.log_msg(f"WARNING: wall {wall_t:.2f}mm < {MIN_WALL_THICKNESS}mm (not printable)")
        if t > MAX_T_SAFE:
            self.log_msg(f"WARNING: t={t:.2f} > {MAX_T_SAFE} (topology transition)")
        if layout["status"] == "truncated":
            self.log_msg(f"NOTE: a={a} not perfectly aligned. Suggested: {layout['suggested_a']:.1f}mm")

        a_str = f"{a:.1f}".replace(".", "")
        t_str = f"{t:.2f}"[2:]
        base_name = f"gyroid_a{a_str}_t{t_str}"

        stl_path = os.path.join(self.output_dir, f"{base_name}.stl")
        step_path = os.path.join(self.output_dir, f"{base_name}.step")

        # ── STL 생성 (고해상도) ──
        if self.stl_var.get():
            self.log_msg(f"[STL] Generating mesh (res={res})...")
            t0 = time.time()
            stl_mesh = self._build_gyroid(a, t, res, include_duct, z_min, z_max,
                                          dual_isosurface=False)
            elapsed = time.time() - t0
            self.log_msg(f"[STL] Mesh done ({len(stl_mesh.faces):,} faces, {elapsed:.1f}s)")
            stl_mesh.export(stl_path, file_type="stl")
            stl_size = os.path.getsize(stl_path) / 1024 / 1024
            self.log_msg(f"[STL] Saved: {stl_path} ({stl_size:.1f} MB)")
            del stl_mesh
            gc.collect()

        # ── STEP 생성 (저해상도) ──
        if self.step_var.get():
            self.log_msg(f"[STEP] Generating mesh (res={step_res})...")
            t0 = time.time()
            step_mesh = self._build_gyroid(a, t, step_res, include_duct, z_min, z_max,
                                           dual_isosurface=False)
            elapsed = time.time() - t0
            n_faces = len(step_mesh.faces)
            self.log_msg(f"[STEP] Mesh done ({n_faces:,} faces, {elapsed:.1f}s)")

            trimesh.repair.fix_normals(step_mesh)
            trimesh.repair.fix_winding(step_mesh)
            step_mesh.merge_vertices()
            step_mesh.process(validate=True)

            tmp_stl = stl_path + ".step_tmp.stl"
            step_mesh.export(tmp_stl, file_type="stl")
            tmp_stl_size = os.path.getsize(tmp_stl) / 1024 / 1024
            self.log_msg(f"[STEP] Temp STL: {n_faces:,} faces, {tmp_stl_size:.1f} MB")
            del step_mesh
            gc.collect()

            self.convert_to_step(tmp_stl, step_path)
            if os.path.isfile(tmp_stl):
                os.remove(tmp_stl)

        # ── 단위셀 STL ──
        if self.unit_cell_var.get():
            self.log_msg(f"[Unit cell] Generating (a={a:.1f}mm, res={res})...")
            t0 = time.time()
            uc_mesh = self._build_unit_cell(a, t, res)
            elapsed = time.time() - t0
            uc_path = os.path.join(self.output_dir, f"{base_name}_unitcell.stl")
            uc_mesh.export(uc_path, file_type="stl")
            uc_size = os.path.getsize(uc_path) / 1024 / 1024
            self.log_msg(f"[Unit cell] Done ({len(uc_mesh.faces):,} faces, {elapsed:.1f}s, {uc_size:.1f} MB)")
            del uc_mesh
            gc.collect()

        # ── 십자 단면 STL (미러 플립) ──
        if self.cross_section_var.get():
            self.log_msg(f"[Cross-section] Mirror-flip generation (res={res})...")
            t0 = time.time()
            cs_mesh = self._build_gyroid(a, t, res, include_duct, z_min, z_max)
            cs_mesh = self._build_cross_section(cs_mesh, gap_mm=25.0)
            elapsed = time.time() - t0
            cs_path = os.path.join(self.output_dir, f"{base_name}_cross_section.stl")
            cs_mesh.export(cs_path, file_type="stl")
            cs_size = os.path.getsize(cs_path) / 1024 / 1024
            self.log_msg(f"[Cross-section] Done ({len(cs_mesh.faces):,} faces, {elapsed:.1f}s, {cs_size:.1f} MB)")
            del cs_mesh
            gc.collect()

        # ── 벽두께 시각화 STL (dual isosurface) ──
        if dual_iso:
            self.log_msg(f"[Thickness vis] Dual isosurface (res={res})...")
            t0 = time.time()
            thick_mesh = self._build_gyroid(a, t, res, include_duct=False,
                                            z_min=z_min, z_max=z_max,
                                            dual_isosurface=True)
            elapsed = time.time() - t0
            thick_path = os.path.join(self.output_dir, f"{base_name}_thickness_vis.stl")
            thick_mesh.export(thick_path, file_type="stl")
            thick_size = os.path.getsize(thick_path) / 1024 / 1024
            self.log_msg(f"[Thickness vis] Done ({len(thick_mesh.faces):,} faces, "
                         f"{elapsed:.1f}s, {thick_size:.1f} MB)")
            del thick_mesh
            gc.collect()

        self.log_msg("=== Done! ===")


if __name__ == "__main__":
    root = tk.Tk()
    app = GyroidApp(root)
    root.mainloop()

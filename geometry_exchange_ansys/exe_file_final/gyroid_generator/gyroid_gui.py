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


DUCT_OUTER = 25.4
WALL = 1.0
DUCT_INNER = DUCT_OUTER - 2 * WALL
TOTAL_Z = 110.0
Z_BUFFER_MM = 5.0
MIN_PRINT_WALL = 1.0  # mm — 3D 프린팅 최소 벽두께


class GyroidApp:
    """Gyroid STL/STEP 생성 GUI. 워커 스레드에서는 Tk 위젯/after 호출 금지 → ui_queue로 메인 스레드에 위임."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Gyroid Catalyst Support - STEP Generator")
        self.root.geometry("620x920")
        self.root.resizable(False, False)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.ui_queue: queue.Queue[tuple] = queue.Queue()
        self.output_dir = os.getcwd()

        self.a_var = tk.DoubleVar(value=5.0)
        self.t_var = tk.DoubleVar(value=0.06)
        self.res_var = tk.IntVar(value=60)
        self.step_res_var = tk.IntVar(value=8)
        self.duct_var = tk.BooleanVar(value=True)
        self.stl_var = tk.BooleanVar(value=True)
        self.step_var = tk.BooleanVar(value=True)
        self.unit_cell_var = tk.BooleanVar(value=False)
        self.cross_section_var = tk.BooleanVar(value=False)
        self.z_buffer_var = tk.BooleanVar(value=True)

        self._build_ui()
        self.root.after(50, self._tick_main_thread)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        param_frame = ttk.LabelFrame(main, text="파라미터 설정", padding=10)
        param_frame.pack(fill="x", padx=4, pady=4)
        param_frame.columnconfigure(1, weight=1)

        ttk.Label(param_frame, text="단위셀 크기 a [mm]:").grid(row=0, column=0, sticky="w")
        ttk.Entry(param_frame, textvariable=self.a_var, width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(param_frame, text="권장 범위: 4.0 ~ 8.0 mm (벽두께 1mm 이상 확보)", foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="두께 파라미터 t:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.t_var, width=12).grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Label(param_frame, text="권장 범위: 0.02 ~ 0.10 (0.11 이상은 위상전이로 벽 소멸)", foreground="gray").grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="STL 해상도 (res):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.res_var, width=12).grid(row=4, column=1, sticky="w", pady=(8, 0))
        ttk.Label(param_frame, text="30=빠름, 60=기본, 120=고품질 (STL 전용)", foreground="gray").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="STEP 해상도:").grid(row=6, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.step_res_var, width=12).grid(row=6, column=1, sticky="w", pady=(8, 0))
        ttk.Label(
            param_frame,
            text="5=빠름(~1분), 8=기본(~2분), 15=고품질(느림) — STEP 전용",
            foreground="gray",
        ).grid(row=7, column=0, columnspan=2, sticky="w")

        ttk.Checkbutton(param_frame, text="외벽 포함 (1.0mm)", variable=self.duct_var).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        ttk.Checkbutton(
            param_frame,
            text="Z 방향 앞·뒤 5mm 버퍼 (Gyroid 도메인을 z=5~105mm로 제한)",
            variable=self.z_buffer_var,
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(
            param_frame,
            text="끄면 z=0~110mm 전체 높이에 Gyroid 생성 (덕트 외벽 옵션과 별개)",
            foreground="gray",
            font=("TkDefaultFont", 8),
        ).grid(row=10, column=0, columnspan=2, sticky="w")

        # 벽두께 표시
        wall_frame = ttk.Frame(param_frame)
        wall_frame.grid(row=11, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(wall_frame, text="예상 최소 벽두께:").pack(side="left")
        self.wall_label = ttk.Label(wall_frame, text="- mm", font=("Consolas", 9, "bold"))
        self.wall_label.pack(side="left", padx=(6, 0))
        ttk.Button(wall_frame, text="계산", command=self._update_wall_thickness, width=6).pack(side="left", padx=(8, 0))
        self.wall_warn_label = ttk.Label(
            param_frame, text="", foreground="red", font=("TkDefaultFont", 8)
        )
        self.wall_warn_label.grid(row=12, column=0, columnspan=2, sticky="w")

        out_frame = ttk.LabelFrame(main, text="출력 설정", padding=10)
        out_frame.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(out_frame, text="STL 저장", variable=self.stl_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="STEP 저장", variable=self.step_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="단위셀 STL (1 unit cell, 외벽 없음)", variable=self.unit_cell_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="십자 단면 STL (내부 구조 확인용)", variable=self.cross_section_var).pack(anchor="w")
        ttk.Label(
            out_frame,
            text="※ STEP은 낮은 해상도로 별도 생성됩니다 (형상 동일, Sewing 속도 확보)",
            foreground="gray",
            font=("TkDefaultFont", 8),
        ).pack(anchor="w", pady=(4, 0))

        path_frame = ttk.Frame(main)
        path_frame.pack(fill="x", padx=4, pady=(4, 8))
        ttk.Label(path_frame, text="출력 폴더:").pack(side="left")
        self.path_label = ttk.Label(path_frame, text=self.output_dir, foreground="gray")
        self.path_label.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(path_frame, text="변경", command=self._choose_output_dir).pack(side="right")

        self.btn = ttk.Button(main, text="생성 시작", command=self.on_generate)
        self.btn.pack(pady=(4, 8))

        log_frame = ttk.LabelFrame(main, text="상태 로그", padding=6)
        log_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.log = scrolledtext.ScrolledText(log_frame, height=14, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        info_frame = ttk.LabelFrame(main, text="수식 / 파라미터 가이드", padding=8)
        info_frame.pack(fill="x", padx=4, pady=4)
        ttk.Label(
            info_frame,
            text=(
                "phi = sin(2*pi*x/a)cos(2*pi*y/a) + sin(2*pi*y/a)cos(2*pi*z/a) + "
                "sin(2*pi*z/a)cos(2*pi*x/a)"
            ),
            font=("Consolas", 8),
        ).pack(anchor="w")
        ttk.Label(
            info_frame,
            text="Solid: phi > -t / Fluid: phi <= -t / Domain: 25.4x25.4x110 mm",
            font=("Consolas", 8),
        ).pack(anchor="w")
        ttk.Label(
            info_frame,
            text="a: 4~8mm | t: 0.02~0.10 (>0.10 위상전이) | 최소벽두께 >= 1mm 권장",
            font=("Consolas", 8),
            foreground="gray",
        ).pack(anchor="w")

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
        """메인 스레드 전용: ui_queue + log_queue 처리 (워커는 여기만 통해 UI 갱신)."""
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

    # ── 벽두께 계산 ──────────────────────────────────────────────

    @staticmethod
    def _calc_min_wall(a: float, t: float, grid_n: int = 150) -> float:
        """단위셀 distance transform으로 최소 벽두께 추정 (mm)."""
        from scipy.ndimage import distance_transform_edt

        voxel = a / grid_n
        lin = np.linspace(0, a, grid_n, endpoint=False) + voxel / 2
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
        # 골격(medial axis) 근사: local maxima of distance field
        from scipy.ndimage import maximum_filter
        local_max = maximum_filter(dt, size=3)
        is_skeleton = (dt == local_max) & solid & (dt > voxel)
        if not is_skeleton.any():
            return float(dt.max()) * 2
        return float(dt[is_skeleton].min()) * 2

    def _update_wall_thickness(self) -> None:
        """GUI 버튼 클릭 시 벽두께 계산 및 표시."""
        a = max(3.0, min(10.0, float(self.a_var.get())))
        t = max(0.01, min(0.50, float(self.t_var.get())))
        wt = self._calc_min_wall(a, t)
        self.wall_label.config(text=f"{wt:.2f} mm")
        if wt < MIN_PRINT_WALL:
            self.wall_label.config(foreground="red")
            self.wall_warn_label.config(
                text=f"⚠ 최소 벽두께 {wt:.2f}mm < {MIN_PRINT_WALL}mm — 3D 프린팅 불가! a를 키우거나 t를 높이세요"
            )
        else:
            self.wall_label.config(foreground="green")
            self.wall_warn_label.config(text=f"✓ 프린팅 가능 (>= {MIN_PRINT_WALL}mm)")

    def on_generate(self) -> None:
        if not self.stl_var.get() and not self.step_var.get() and not self.unit_cell_var.get():
            messagebox.showwarning("출력 설정 필요", "STL, STEP, 단위셀 중 최소 1개를 선택하세요.")
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

    # ── 자이로이드 메시 생성 (공통 로직) ──────────────────────────

    def _build_gyroid(self, a: float, t: float, res: int,
                      include_duct: bool, z_min: float, z_max: float) -> "trimesh.Trimesh":
        """주어진 해상도로 자이로이드 메시를 생성하여 반환."""
        x_min, x_max_coord = WALL, DUCT_OUTER - WALL
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
        verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=spacing)
        verts[:, 0] += x_min
        verts[:, 1] += x_min
        verts[:, 2] += z_min

        gyroid_mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        combined = gyroid_mesh

        if include_duct:
            self.log_msg("   외벽 결합 중 (Manifold)...")
            outer_box = trimesh.creation.box(extents=[DUCT_OUTER, DUCT_OUTER, TOTAL_Z])
            outer_box.apply_translation([DUCT_OUTER / 2, DUCT_OUTER / 2, TOTAL_Z / 2])
            inner_box = trimesh.creation.box(extents=[DUCT_INNER, DUCT_INNER, TOTAL_Z + 2])
            inner_box.apply_translation([DUCT_OUTER / 2, DUCT_OUTER / 2, TOTAL_Z / 2])
            duct_wall = outer_box.difference(inner_box, engine="manifold")
            combined = trimesh.util.concatenate([gyroid_mesh, duct_wall])

        return combined

    def _build_unit_cell(self, a: float, t: float, res: int) -> "trimesh.Trimesh":
        """단위셀 1개 (a×a×a mm 정육면체) 자이로이드 메시 생성. 외벽 없음."""
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
        """메시를 XY 중심으로 십자 분할 후 gap만큼 벌려서 내부가 보이게 한다."""
        bounds = mesh.bounds  # [[xmin,ymin,zmin],[xmax,ymax,zmax]]
        cx = (bounds[0][0] + bounds[1][0]) / 2
        cy = (bounds[0][1] + bounds[1][1]) / 2

        # 4분할: slice_mesh_plane(plane_origin, plane_normal) → normal 방향 쪽 유지
        try:
            xp = mesh.slice_plane([cx, 0, 0], [1, 0, 0], cap=True)  # x > cx
            xn = mesh.slice_plane([cx, 0, 0], [-1, 0, 0], cap=True)  # x < cx
            q1 = xp.slice_plane([0, cy, 0], [0, 1, 0], cap=True)  # x>cx, y>cy
            q2 = xn.slice_plane([0, cy, 0], [0, 1, 0], cap=True)  # x<cx, y>cy
            q3 = xn.slice_plane([0, cy, 0], [0, -1, 0], cap=True)  # x<cx, y<cy
            q4 = xp.slice_plane([0, cy, 0], [0, -1, 0], cap=True)  # x>cx, y<cy
        except Exception as e:
            self.log_msg(f"   단면 분할 실패: {e}")
            return mesh

        # 각 사분면을 gap만큼 바깥으로 이동
        dx, dy = gap_mm / 2, gap_mm / 2
        q1.apply_translation([+dx, +dy, 0])
        q2.apply_translation([-dx, +dy, 0])
        q3.apply_translation([-dx, -dy, 0])
        q4.apply_translation([+dx, -dy, 0])

        parts = [q for q in [q1, q2, q3, q4] if len(q.faces) > 0]
        if not parts:
            self.log_msg("   단면 분할 결과 빈 메시")
            return mesh
        return trimesh.util.concatenate(parts)

    # ── STEP 변환 (별도 프로세스) ──────────────────────────────────

    @staticmethod
    def _find_converter() -> str:
        """step_converter.py 또는 step_converter.exe 경로를 찾는다."""
        # PyInstaller onedir: exe 옆에 step_converter.exe 또는 _internal 안
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
            for name in ("step_converter.exe", "step_converter"):
                p = os.path.join(base, name)
                if os.path.isfile(p):
                    return p
            # _internal 안의 .py 파일
            p = os.path.join(base, "_internal", "step_converter.py")
            if os.path.isfile(p):
                return p
        # 개발 환경: 같은 폴더의 .py
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step_converter.py")
        if os.path.isfile(p):
            return p
        return ""

    def convert_to_step(self, stl_path: str, step_path: str) -> bool:
        """별도 프로세스에서 STEP 변환 실행 — GUI 멈춤 방지."""
        converter = self._find_converter()
        if not converter:
            self.log_msg("   step_converter를 찾을 수 없음")
            return False

        stl_abs = str(Path(stl_path).resolve())
        step_abs = str(Path(step_path).resolve())

        # 실행 명령 결정
        if converter.endswith(".py"):
            cmd = [sys.executable, converter, stl_abs, step_abs]
        else:
            cmd = [converter, stl_abs, step_abs]

        self.log_msg(f"   STEP 변환 프로세스 시작...")
        self.log_msg(f"   CMD: {os.path.basename(converter)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            # 실시간 로그 읽기 (바이너리 → UTF-8, 디코딩 오류 무시)
            for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                if line:
                    self.log_msg(f"   {line}")

            proc.wait()
            if proc.returncode == 0:
                if os.path.isfile(step_abs):
                    size_mb = os.path.getsize(step_abs) / 1024 / 1024
                    self.log_msg(f"   STEP 저장 완료 ({size_mb:.1f} MB)")
                return True
            else:
                self.log_msg(f"   STEP 변환 실패 (exit code {proc.returncode})")
                return False
        except Exception as exc:
            self.log_msg(f"   STEP 프로세스 실행 오류: {exc}")
            return False

    # ── 메인 생성 흐름 ──────────────────────────────────────────

    def do_generate(self) -> None:
        a = max(3.0, min(10.0, float(self.a_var.get())))
        t = max(0.01, min(0.50, float(self.t_var.get())))
        res = max(30, min(120, int(self.res_var.get())))
        step_res = max(3, min(15, int(self.step_res_var.get())))
        include_duct = bool(self.duct_var.get())
        use_z_buffer = bool(self.z_buffer_var.get())

        if use_z_buffer:
            z_min, z_max = Z_BUFFER_MM, TOTAL_Z - Z_BUFFER_MM
            z_note = f"z=[{z_min},{z_max}]mm (버퍼 {Z_BUFFER_MM}mm)"
        else:
            z_min, z_max = 0.0, TOTAL_Z
            z_note = f"z=[0,{TOTAL_Z}]mm (버퍼 없음)"

        # 벽두께 검증
        wall_t = self._calc_min_wall(a, t)
        self.log_msg(f"파라미터: a={a}mm, t={t}, 외벽={include_duct}, {z_note}")
        self.log_msg(f"해상도: STL={res}, STEP={step_res}")
        self.log_msg(f"예상 최소 벽두께: {wall_t:.2f} mm")
        if wall_t < MIN_PRINT_WALL:
            self.log_msg(
                f"⚠ 벽두께 {wall_t:.2f}mm < {MIN_PRINT_WALL}mm — 3D 프린팅 최소 조건 미달!"
            )
            self.log_msg("  → a를 키우거나 t를 높여 벽두께를 확보하세요. 생성은 계속 진행합니다.")

        a_str = f"{a:.1f}".replace(".", "")
        t_str = f"{t:.2f}"[2:]
        buf_tag = "buf" if use_z_buffer else "fullz"
        base_name = f"gyroid_a{a_str}_t{t_str}_{buf_tag}"

        stl_path = os.path.join(self.output_dir, f"{base_name}.stl")
        step_path = os.path.join(self.output_dir, f"{base_name}.step")

        # ── STL 생성 (고해상도) ──
        if self.stl_var.get():
            self.log_msg(f"[STL] 해상도 {res}로 형상 생성 중...")
            t0 = time.time()
            stl_mesh = self._build_gyroid(a, t, res, include_duct, z_min, z_max)
            elapsed = time.time() - t0
            self.log_msg(f"[STL] 형상 완료 (면 수: {len(stl_mesh.faces):,}, {elapsed:.1f}초)")

            stl_mesh.export(stl_path, file_type="stl")
            stl_size = os.path.getsize(stl_path) / 1024 / 1024
            self.log_msg(f"[STL] 저장 완료: {stl_path} ({stl_size:.1f} MB)")
            del stl_mesh
            gc.collect()

        # ── STEP 생성 (저해상도로 별도 생성) ──
        if self.step_var.get():
            self.log_msg(f"[STEP] 해상도 {step_res}로 형상 생성 중 (STL과 별도)...")
            t0 = time.time()
            step_mesh = self._build_gyroid(a, t, step_res, include_duct, z_min, z_max)
            elapsed = time.time() - t0
            n_faces = len(step_mesh.faces)
            self.log_msg(f"[STEP] 형상 완료 (면 수: {n_faces:,}, {elapsed:.1f}초)")

            # 메시 정리
            trimesh.repair.fix_normals(step_mesh)
            trimesh.repair.fix_winding(step_mesh)
            step_mesh.merge_vertices()
            step_mesh.process(validate=True)

            # 임시 STL 생성 → OCP로 STEP 변환
            tmp_stl = stl_path + ".step_tmp.stl"
            step_mesh.export(tmp_stl, file_type="stl")
            tmp_stl_size = os.path.getsize(tmp_stl) / 1024 / 1024
            self.log_msg(f"[STEP] 임시 STL: {n_faces:,} 면, {tmp_stl_size:.1f} MB")
            del step_mesh
            gc.collect()

            self.convert_to_step(tmp_stl, step_path)

            # 임시 파일 정리
            if os.path.isfile(tmp_stl):
                os.remove(tmp_stl)

        # ── 단위셀 STL (1 unit cell, 외벽 없음) ──
        if self.unit_cell_var.get():
            self.log_msg(f"[단위셀] 해상도 {res}로 단위셀 생성 중 (a={a}mm 정육면체)...")
            t0 = time.time()
            uc_mesh = self._build_unit_cell(a, t, res)
            elapsed = time.time() - t0
            uc_path = os.path.join(self.output_dir, f"{base_name}_unitcell.stl")
            uc_mesh.export(uc_path, file_type="stl")
            uc_size = os.path.getsize(uc_path) / 1024 / 1024
            self.log_msg(
                f"[단위셀] 완료 (면 수: {len(uc_mesh.faces):,}, {elapsed:.1f}초, {uc_size:.1f} MB)"
            )
            self.log_msg(f"[단위셀] 저장: {uc_path}")
            del uc_mesh
            gc.collect()

        # ── 십자 단면 STL (내부 확인용) ──
        if self.cross_section_var.get():
            self.log_msg(f"[단면] 십자 단면 STL 생성 중 (해상도 {res})...")
            t0 = time.time()
            cs_mesh = self._build_gyroid(a, t, res, include_duct, z_min, z_max)
            cs_mesh = self._build_cross_section(cs_mesh, gap_mm=5.0)
            elapsed = time.time() - t0
            cs_path = os.path.join(self.output_dir, f"{base_name}_cross_section.stl")
            cs_mesh.export(cs_path, file_type="stl")
            cs_size = os.path.getsize(cs_path) / 1024 / 1024
            self.log_msg(
                f"[단면] 완료 (면 수: {len(cs_mesh.faces):,}, {elapsed:.1f}초, {cs_size:.1f} MB)"
            )
            self.log_msg(f"[단면] 저장: {cs_path}")
            del cs_mesh
            gc.collect()

        self.log_msg("완료!")


if __name__ == "__main__":
    root = tk.Tk()
    app = GyroidApp(root)
    root.mainloop()

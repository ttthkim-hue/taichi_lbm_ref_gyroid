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
        self.t_var = tk.DoubleVar(value=0.3)
        self.res_var = tk.IntVar(value=60)
        self.step_res_var = tk.IntVar(value=8)
        self.duct_var = tk.BooleanVar(value=True)
        self.stl_var = tk.BooleanVar(value=True)
        self.step_var = tk.BooleanVar(value=True)
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
        ttk.Label(param_frame, text="권장 범위: 3.0 ~ 8.0 mm", foreground="gray").grid(
            row=1, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(param_frame, text="두께 파라미터 t:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.t_var, width=12).grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Label(param_frame, text="권장 범위: 0.05 ~ 0.50", foreground="gray").grid(
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

        out_frame = ttk.LabelFrame(main, text="출력 설정", padding=10)
        out_frame.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(out_frame, text="STL 저장", variable=self.stl_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="STEP 저장", variable=self.step_var).pack(anchor="w")
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
            text="a: 3~8 mm | t: 0.05~0.5 | 버퍼 ON 시 Gyroid z 구간만 5~105mm",
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

    def on_generate(self) -> None:
        if not self.stl_var.get() and not self.step_var.get():
            messagebox.showwarning("출력 설정 필요", "STL 또는 STEP 중 최소 1개를 선택하세요.")
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
        a = max(3.0, min(8.0, float(self.a_var.get())))
        t = max(0.05, min(0.5, float(self.t_var.get())))
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

        self.log_msg(f"파라미터: a={a}mm, t={t}, 외벽={include_duct}, {z_note}")
        self.log_msg(f"해상도: STL={res}, STEP={step_res}")

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

        self.log_msg("완료!")


if __name__ == "__main__":
    root = tk.Tk()
    app = GyroidApp(root)
    root.mainloop()

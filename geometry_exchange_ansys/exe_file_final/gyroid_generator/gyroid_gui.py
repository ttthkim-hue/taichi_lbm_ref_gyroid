#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gc
import os
import queue
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
        self.root.geometry("620x900")
        self.root.resizable(False, False)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.ui_queue: queue.Queue[tuple] = queue.Queue()
        self.output_dir = os.getcwd()

        self.a_var = tk.DoubleVar(value=5.0)
        self.t_var = tk.DoubleVar(value=0.3)
        self.res_var = tk.IntVar(value=60)
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

        ttk.Label(param_frame, text="해상도 (res):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(param_frame, textvariable=self.res_var, width=12).grid(row=4, column=1, sticky="w", pady=(8, 0))
        ttk.Label(param_frame, text="30=빠름, 60=기본, 120=고품질", foreground="gray").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        ttk.Checkbutton(param_frame, text="외벽 포함 (1.0mm)", variable=self.duct_var).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        ttk.Checkbutton(
            param_frame,
            text="Z 방향 앞·뒤 5mm 버퍼 (Gyroid 도메인을 z=5~105mm로 제한)",
            variable=self.z_buffer_var,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(
            param_frame,
            text="끄면 z=0~110mm 전체 높이에 Gyroid 생성 (덕트 외벽 옵션과 별개)",
            foreground="gray",
            font=("TkDefaultFont", 8),
        ).grid(row=8, column=0, columnspan=2, sticky="w")

        out_frame = ttk.LabelFrame(main, text="출력 설정", padding=10)
        out_frame.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(out_frame, text="STL 저장", variable=self.stl_var).pack(anchor="w")
        ttk.Checkbutton(out_frame, text="STEP 저장", variable=self.step_var).pack(anchor="w")
        ttk.Label(
            out_frame,
            text="※ STEP은 STL보다 오래 걸립니다. 면 수가 많으면 수 분~10분 이상일 수 있습니다.",
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
                elif cmd[0] == "vars":
                    a, t, res = cmd[1], cmd[2], cmd[3]
                    self.a_var.set(a)
                    self.t_var.set(t)
                    self.res_var.set(res)
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

    def _ui_vars(self, a: float, t: float, res: int) -> None:
        self.ui_queue.put(("vars", a, t, res))

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
            self.log_msg(f"❌ 오류: {exc}")
            import traceback

            self.log_msg(traceback.format_exc())
        finally:
            self._ui_btn(True)

    def convert_to_step(self, stl_path: str, step_path: str) -> bool:
        self.log_msg("🔄 STEP 변환 시작 (OCP) — 면이 많으면 수 분 이상 걸릴 수 있습니다.")
        try:
            from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
            from OCP.Interface import Interface_Static
            from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
            from OCP.StlAPI import StlAPI_Reader
            from OCP.TopAbs import TopAbs_SHELL
            from OCP.TopoDS import TopoDS, TopoDS_Shape
            from OCP.TopExp import TopExp_Explorer
        except ImportError as exc:
            self.log_msg(f"⚠️ OCP(cadquery) 없음 — STEP 생략: {exc}")
            self.log_msg("   Windows exe는 cadquery 포함 빌드 필요 (GitHub Actions 최신 워크플로)")
            self.log_msg("   대안: SpaceClaim에서 STL → Convert to Solid → STEP")
            return False

        stl_abs = str(Path(stl_path).resolve())
        step_abs = str(Path(step_path).resolve())

        try:
            self.log_msg("   (1/4) STL 파일 로드 (OCP Reader)...")
            reader = StlAPI_Reader()
            shape = TopoDS_Shape()
            if not reader.Read(shape, stl_abs):
                self.log_msg(f"❌ STL 읽기 실패: {stl_abs}")
                return False

            self.log_msg("   (2/4) Sewing(봉제) — 가장 오래 걸리는 단계일 수 있음...")
            t_sew = time.time()
            sewing = BRepBuilderAPI_Sewing(0.1)
            sewing.Add(shape)
            sewing.Perform()
            sewn = sewing.SewedShape()
            self.log_msg(f"      sewing 완료 ({time.time() - t_sew:.1f}s)")

            result = sewn
            self.log_msg("   (3/4) Shell → Solid 시도...")
            try:
                explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
                if explorer.More():
                    shell = TopoDS.Shell_s(explorer.Current())
                    maker = BRepBuilderAPI_MakeSolid(shell)
                    if maker.IsDone():
                        result = maker.Solid()
            except Exception as exc:
                self.log_msg(f"      Solid화 생략(셸 유지): {exc}")

            self.log_msg("   (4/4) STEP 파일 쓰기...")
            t_w = time.time()
            writer = STEPControl_Writer()
            Interface_Static.SetCVal_s("write.step.schema", "AP214")
            writer.Transfer(result, STEPControl_AsIs)
            status = writer.Write(step_abs)
            self.log_msg(f"      write 호출 완료 ({time.time() - t_w:.1f}s), status={status}")

            if status == 1 and os.path.isfile(step_abs):
                size_mb = os.path.getsize(step_abs) / 1024 / 1024
                self.log_msg(f"✅ STEP 저장: {step_abs} ({size_mb:.1f} MB)")
                return True

            self.log_msg(f"❌ STEP 저장 실패 (status={status})")
            return False
        except Exception as exc:
            self.log_msg(f"❌ STEP 변환 예외: {exc}")
            import traceback

            self.log_msg(traceback.format_exc())
            return False

    def do_generate(self) -> None:
        a = float(self.a_var.get())
        t = float(self.t_var.get())
        res = int(self.res_var.get())
        include_duct = bool(self.duct_var.get())
        use_z_buffer = bool(self.z_buffer_var.get())

        a = max(3.0, min(8.0, a))
        t = max(0.05, min(0.5, t))
        res = max(30, min(120, res))

        self._ui_vars(a, t, res)

        if use_z_buffer:
            z_min, z_max = Z_BUFFER_MM, TOTAL_Z - Z_BUFFER_MM
            z_note = f"z∈[{z_min},{z_max}]mm (버퍼 {Z_BUFFER_MM}mm)"
        else:
            z_min, z_max = 0.0, TOTAL_Z
            z_note = f"z∈[0,{TOTAL_Z}]mm (버퍼 없음)"

        self.log_msg(
            f"✅ 파라미터: a={a} mm, t={t}, res={res}, 외벽={include_duct}, {z_note}"
        )
        self.log_msg("🏗️ 형상 생성 시작...")
        t0 = time.time()

        x_min, x_max = WALL, DUCT_OUTER - WALL
        nx = max(20, int((x_max - x_min) / a * res))
        ny = nx
        nz = max(20, int((z_max - z_min) / a * res))

        x_range = np.linspace(x_min, x_max, nx)
        y_range = np.linspace(x_min, x_max, ny)
        z_range = np.linspace(z_min, z_max, nz)
        x_grid, y_grid, z_grid = np.meshgrid(x_range, y_range, z_range, indexing="ij")

        k = 2.0 * np.pi / a
        phi = (
            np.sin(k * x_grid) * np.cos(k * y_grid)
            + np.sin(k * y_grid) * np.cos(k * z_grid)
            + np.sin(k * z_grid) * np.cos(k * x_grid)
        )

        spacing = (
            (x_max - x_min) / (nx - 1),
            (x_max - x_min) / (ny - 1),
            (z_max - z_min) / (nz - 1),
        )
        verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=spacing)
        verts[:, 0] += x_min
        verts[:, 1] += x_min
        verts[:, 2] += z_min

        gyroid_mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        combined = gyroid_mesh

        if include_duct:
            self.log_msg("🧱 외벽 결합 중 (Manifold Engine 사용)...")
            outer_box = trimesh.creation.box(extents=[DUCT_OUTER, DUCT_OUTER, TOTAL_Z])
            outer_box.apply_translation([DUCT_OUTER / 2, DUCT_OUTER / 2, TOTAL_Z / 2])
            inner_box = trimesh.creation.box(extents=[DUCT_INNER, DUCT_INNER, TOTAL_Z + 2])
            inner_box.apply_translation([DUCT_OUTER / 2, DUCT_OUTER / 2, TOTAL_Z / 2])
            try:
                duct_wall = outer_box.difference(inner_box, engine="manifold")
                combined = trimesh.util.concatenate([gyroid_mesh, duct_wall])
                self.log_msg("✅ 외벽 결합 성공")
            except Exception as exc:
                self.log_msg(f"❌ 외벽 결합 실패: {exc}")
                raise
        else:
            self.log_msg("ℹ️ 외벽 미포함 옵션으로 진행")

        elapsed = time.time() - t0
        self.log_msg(f"✨ 형상 생성 완료 (면 수: {len(combined.faces):,}, 소요시간: {elapsed:.1f}초)")

        a_str = f"{a:.1f}".replace(".", "")
        t_str = f"{t:.2f}"[2:]
        buf_tag = "buf" if use_z_buffer else "fullz"
        base_name = f"gyroid_a{a_str}_t{t_str}_{buf_tag}"

        stl_path = os.path.join(self.output_dir, f"{base_name}.stl")
        step_path = os.path.join(self.output_dir, f"{base_name}.step")

        if self.stl_var.get():
            combined.export(stl_path, file_type="stl")
            stl_size = os.path.getsize(stl_path) / 1024 / 1024
            self.log_msg(f"✅ STL 저장: {stl_path} ({stl_size:.1f} MB)")

        if self.step_var.get():
            if not os.path.exists(stl_path):
                combined.export(stl_path, file_type="stl")
                self.log_msg("ℹ️ STEP 변환을 위해 STL 임시 저장")
            # OCP가 STL을 다시 읽으므로 Python 쪽 대용량 메쉬 해제
            try:
                del combined
                del gyroid_mesh
                del verts, faces, phi, x_grid, y_grid, z_grid
            except Exception:
                pass
            gc.collect()
            self.log_msg("⏳ 메모리 정리 후 STEP 변환 진행...")
            self.convert_to_step(stl_path, step_path)

        self.log_msg("🎉 완료!")


if __name__ == "__main__":
    root = tk.Tk()
    app = GyroidApp(root)
    root.mainloop()

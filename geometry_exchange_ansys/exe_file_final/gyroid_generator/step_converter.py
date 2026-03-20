#!/usr/bin/env python3
"""STEP converter — runs as a separate process from the main GUI.
Usage: python step_converter.py <input.stl> <output.step>
Progress is printed to stdout (read by the GUI).
"""
import os
import sys
import threading
import time


def _estimate_sewing_sec(n_faces: int) -> float:
    """Estimate sewing time based on face count. Benchmark: 12K faces = 5s."""
    return 5.0 * (n_faces / 12000) ** 1.4


def main():
    if len(sys.argv) != 3:
        print("[ERROR] Usage: step_converter.py <input.stl> <output.step>")
        sys.exit(1)

    stl_path = os.path.abspath(sys.argv[1])
    step_path = os.path.abspath(sys.argv[2])

    if not os.path.isfile(stl_path):
        print(f"[ERROR] STL not found: {stl_path}")
        sys.exit(1)

    stl_size = os.path.getsize(stl_path)
    est_faces = max(1, (stl_size - 84) // 50)
    est_sec = _estimate_sewing_sec(est_faces)

    print("[INFO] Loading OCP modules...")
    sys.stdout.flush()
    try:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
        from OCP.Interface import Interface_Static
        from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCP.StlAPI import StlAPI_Reader
        from OCP.TopAbs import TopAbs_SHELL
        from OCP.TopoDS import TopoDS, TopoDS_Shape
        from OCP.TopExp import TopExp_Explorer
        print("[OK] OCP loaded")
    except ImportError as e:
        print(f"[ERROR] OCP import failed: {e}")
        sys.exit(1)
    sys.stdout.flush()

    print(f"[INFO] (1/4) Loading STL ({stl_size / 1024 / 1024:.1f} MB)...")
    sys.stdout.flush()
    reader = StlAPI_Reader()
    shape = TopoDS_Shape()
    if not reader.Read(shape, stl_path):
        print("[ERROR] STL read failed")
        sys.exit(1)
    print(f"[OK] STL loaded (null={shape.IsNull()})")
    sys.stdout.flush()

    print(f"[INFO] (2/4) Sewing ~{est_faces:,} faces (est. {est_sec:.0f}s)...")
    sys.stdout.flush()

    sewing = BRepBuilderAPI_Sewing(0.1)
    sewing.SetNonManifoldMode(True)
    sewing.Add(shape)

    sew_done = threading.Event()
    t0 = time.time()

    def _do_sew():
        sewing.Perform()
        sew_done.set()

    threading.Thread(target=_do_sew, daemon=True).start()

    while not sew_done.wait(timeout=3.0):
        elapsed = time.time() - t0
        pct = min(99, int(elapsed / max(est_sec, 1) * 100))
        print(f"[SEWING] {elapsed:.0f}s / ~{est_sec:.0f}s ({pct}%)")
        sys.stdout.flush()

    elapsed = time.time() - t0
    sewn = sewing.SewedShape()
    print(f"[OK] Sewing done ({elapsed:.1f}s, null={sewn.IsNull()})")
    sys.stdout.flush()

    if sewn.IsNull():
        print("[ERROR] Sewing result is null")
        sys.exit(1)

    result = sewn
    print("[INFO] (3/4) Shell -> Solid...")
    sys.stdout.flush()
    try:
        explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
        if explorer.More():
            shell = TopoDS.Shell_s(explorer.Current())
            maker = BRepBuilderAPI_MakeSolid(shell)
            if maker.IsDone():
                result = maker.Solid()
                print("[OK] Solid conversion succeeded")
            else:
                print("[WARN] Solid failed, using shell")
        else:
            print("[WARN] No shell found, using sewn shape")
    except Exception as e:
        print(f"[WARN] Solid skipped: {e}")
    sys.stdout.flush()

    print("[INFO] (4/4) Writing STEP (AP214)...")
    sys.stdout.flush()
    t_w = time.time()
    writer = STEPControl_Writer()
    Interface_Static.SetCVal_s("write.step.schema", "AP214")
    writer.Transfer(result, STEPControl_AsIs)
    wr_status = writer.Write(step_path)
    print(f"[INFO] Write status={wr_status} ({time.time() - t_w:.1f}s)")
    sys.stdout.flush()

    if wr_status == 1 and os.path.isfile(step_path):
        size_mb = os.path.getsize(step_path) / 1024 / 1024
        print(f"[DONE] STEP saved: {size_mb:.1f} MB")
        sys.exit(0)
    else:
        print(f"[ERROR] STEP write failed (status={wr_status})")
        sys.exit(1)


if __name__ == "__main__":
    main()

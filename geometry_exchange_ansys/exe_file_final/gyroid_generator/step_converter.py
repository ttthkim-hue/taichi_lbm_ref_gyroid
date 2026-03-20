#!/usr/bin/env python3
"""STEP 변환 전용 스크립트 — 메인 GUI와 별도 프로세스로 실행.
사용법: python step_converter.py <input.stl> <output.step>
stdout에 진행 상황 출력 (메인 GUI가 읽음).
"""
import os
import sys
import threading
import time


def _estimate_sewing_sec(n_faces: int) -> float:
    """면 수 기반 sewing 예상 시간 (초). CI 벤치마크: 12K면=5s."""
    # sewing은 대략 O(n^1.3) ~ O(n^1.5) 스케일링
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

    # STL 파일 크기로 면 수 추정 (binary STL: 80 header + 4 bytes + 50 bytes/face)
    stl_size = os.path.getsize(stl_path)
    est_faces = max(1, (stl_size - 84) // 50)
    est_sec = _estimate_sewing_sec(est_faces)

    print("[INFO] OCP 모듈 로딩 중...")
    sys.stdout.flush()
    try:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
        from OCP.Interface import Interface_Static
        from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCP.StlAPI import StlAPI_Reader
        from OCP.TopAbs import TopAbs_SHELL
        from OCP.TopoDS import TopoDS, TopoDS_Shape
        from OCP.TopExp import TopExp_Explorer
        print("[OK] OCP 로딩 성공")
    except ImportError as e:
        print(f"[ERROR] OCP import 실패: {e}")
        sys.exit(1)
    sys.stdout.flush()

    print(f"[INFO] (1/4) STL 로드: {stl_path}")
    sys.stdout.flush()
    reader = StlAPI_Reader()
    shape = TopoDS_Shape()
    if not reader.Read(shape, stl_path):
        print("[ERROR] STL 읽기 실패")
        sys.exit(1)
    print(f"[OK] STL 로드 완료 (null={shape.IsNull()})")
    sys.stdout.flush()

    # ── Sewing을 스레드에서 실행, 메인 스레드가 경과시간 출력 ──
    print(f"[INFO] (2/4) Sewing 시작 (~{est_faces:,}면, 예상 {est_sec:.0f}초)...")
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

    # 3초마다 경과시간 출력
    while not sew_done.wait(timeout=3.0):
        elapsed = time.time() - t0
        pct = min(99, int(elapsed / max(est_sec, 1) * 100))
        print(f"[SEWING] {elapsed:.0f}s 경과 / 예상 ~{est_sec:.0f}s ({pct}%)")
        sys.stdout.flush()

    elapsed = time.time() - t0
    sewn = sewing.SewedShape()
    print(f"[OK] Sewing 완료 ({elapsed:.1f}s, null={sewn.IsNull()})")
    sys.stdout.flush()

    if sewn.IsNull():
        print("[ERROR] Sewing 결과가 null")
        sys.exit(1)

    result = sewn
    print("[INFO] (3/4) Shell → Solid 변환...")
    sys.stdout.flush()
    try:
        explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
        if explorer.More():
            shell = TopoDS.Shell_s(explorer.Current())
            maker = BRepBuilderAPI_MakeSolid(shell)
            if maker.IsDone():
                result = maker.Solid()
                print("[OK] Solid 변환 성공")
            else:
                print("[WARN] Solid 변환 실패 → Shell로 진행")
        else:
            print("[WARN] Shell 없음 → sewn shape으로 진행")
    except Exception as e:
        print(f"[WARN] Solid화 생략: {e}")
    sys.stdout.flush()

    print("[INFO] (4/4) STEP 쓰기 (AP214)...")
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
        print(f"[DONE] STEP 저장 완료: {step_path} ({size_mb:.1f} MB)")
        sys.exit(0)
    else:
        print(f"[ERROR] STEP 저장 실패 (status={wr_status})")
        sys.exit(1)


if __name__ == "__main__":
    main()

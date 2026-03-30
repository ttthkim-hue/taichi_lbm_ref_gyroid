#!/usr/bin/env python3
"""
STEP Assembly converter — ISO 10303-214 (AP214) Assembly STEP 생성.

단위셀 mesh를 XCAF PRODUCT_DEFINITION으로 1회만 정의하고,
NEXT_ASSEMBLY_USAGE_OCCURENCE로 격자 위치에 N회 인스턴싱.
→ 파일 크기: 단위셀 정의(~50-200 KB) + 인스턴스 참조(~200 bytes × N) = 수백 KB

Usage:
    step_converter_assembly.py <a> <t> <res_cell> <n_xy> <n_z>
                               <z_start> <xy_start> <include_duct> <output.step>

Args:
    a           단위셀 크기 [mm]
    t           두께 파라미터
    res_cell    단위셀당 voxel 수 (15~40 권장)
    n_xy        XY 방향 셀 개수
    n_z         Z 방향 셀 개수
    z_start     자이로이드 Z 시작 [mm]
    xy_start    자이로이드 XY 시작 [mm] (= GYROID_XY_START = 0.7)
    include_duct 1=덕트벽 포함, 0=제외
    output.step 출력 파일 경로
"""
import os
import sys
import tempfile
import time

import numpy as np


# ── 고정 규격 ──
DUCT_OUTER = 25.4
DUCT_WALL  = 1.0
TOTAL_Z    = 110.0


def _make_unit_cell_ocp(a: float, t: float, res: int):
    """
    단위셀 1개 (a×a×a mm) marching_cubes → 임시 STL → OCP sewed shell.
    반환: TopoDS_Shape (shell, possibly open at periodic boundaries)
    """
    from skimage.measure import marching_cubes
    import trimesh

    n = max(15, int(res))
    lin = np.linspace(0.0, a, n)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    k = 2.0 * np.pi / a
    phi = (
        np.sin(k * X) * np.cos(k * Y)
        + np.sin(k * Y) * np.cos(k * Z)
        + np.sin(k * Z) * np.cos(k * X)
    )
    sp = a / (n - 1)
    verts, faces, _, _ = marching_cubes(phi, level=-t, spacing=(sp, sp, sp))
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)

    tmp = tempfile.mktemp(suffix=".stl")
    mesh.export(tmp, file_type="stl")

    from OCP.StlAPI import StlAPI_Reader
    from OCP.TopoDS import TopoDS_Shape as _Shape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing

    shape = _Shape()
    if not StlAPI_Reader().Read(shape, tmp):
        os.remove(tmp)
        raise RuntimeError("OCP StlAPI_Reader failed on unit cell STL")
    os.remove(tmp)

    sew = BRepBuilderAPI_Sewing(sp * 0.05)
    sew.Add(shape)
    sew.Perform()
    result = sew.SewedShape()
    if result.IsNull():
        raise RuntimeError("Sewing of unit cell returned null shape")
    return result


def _make_duct_wall_ocp():
    """
    덕트벽 = 외부 박스 − 내부 박스 → B-rep solid.
    STEP에서 수십 바이트 수준의 compact 표현.
    """
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Pnt

    outer = BRepPrimAPI_MakeBox(
        gp_Pnt(0.0, 0.0, 0.0),
        gp_Pnt(DUCT_OUTER, DUCT_OUTER, TOTAL_Z),
    ).Shape()
    inner = BRepPrimAPI_MakeBox(
        gp_Pnt(DUCT_WALL, DUCT_WALL, 0.0),
        gp_Pnt(DUCT_OUTER - DUCT_WALL, DUCT_OUTER - DUCT_WALL, TOTAL_Z),
    ).Shape()
    cut = BRepAlgoAPI_Cut(outer, inner)
    cut.Build()
    if not cut.IsDone():
        raise RuntimeError("Duct wall boolean cut failed")
    return cut.Shape()


def main() -> None:
    if len(sys.argv) != 10:
        print(f"[ERROR] Need 9 args, got {len(sys.argv) - 1}")
        print(__doc__)
        sys.exit(1)

    a         = float(sys.argv[1])
    t         = float(sys.argv[2])
    res_cell  = int(sys.argv[3])
    n_xy      = int(sys.argv[4])
    n_z       = int(sys.argv[5])
    z_start   = float(sys.argv[6])
    xy_start  = float(sys.argv[7])
    inc_duct  = sys.argv[8].lower() in ("1", "true", "yes")
    out_path  = os.path.abspath(sys.argv[9])

    total_inst = n_xy * n_xy * n_z
    print(f"[INFO] Assembly STEP: a={a}mm t={t} res_cell={res_cell}")
    print(f"[INFO] Grid: {n_xy}x{n_xy}x{n_z} = {total_inst} instances")
    print(f"[INFO] Z=[{z_start:.1f}, {z_start + n_z * a:.1f}]mm, XY_start={xy_start:.2f}mm")
    print(f"[INFO] Duct wall: {'yes' if inc_duct else 'no'}")
    sys.stdout.flush()

    print("[INFO] Loading OCP modules...")
    sys.stdout.flush()
    try:
        from OCP.XCAFApp import XCAFApp_Application
        from OCP.XCAFDoc import XCAFDoc_DocumentTool
        from OCP.STEPCAFControl import STEPCAFControl_Writer
        from OCP.TDocStd import TDocStd_Document
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.TDataStd import TDataStd_Name
        from OCP.gp import gp_Trsf, gp_Vec
        from OCP.TopLoc import TopLoc_Location
        from OCP.Interface import Interface_Static
        print("[OK] OCP loaded")
    except ImportError as e:
        print(f"[ERROR] OCP import failed: {e}")
        sys.exit(1)
    sys.stdout.flush()

    print(f"[INFO] (1/4) Building unit cell (res={res_cell})...")
    sys.stdout.flush()
    t0 = time.time()
    try:
        cell_shape = _make_unit_cell_ocp(a, t, res_cell)
    except Exception as e:
        print(f"[ERROR] Unit cell failed: {e}")
        sys.exit(1)
    print(f"[OK] Unit cell done ({time.time() - t0:.1f}s, null={cell_shape.IsNull()})")
    sys.stdout.flush()

    print(f"[INFO] (2/4) XCAF Assembly ({total_inst} instances)...")
    sys.stdout.flush()
    t0 = time.time()

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    app.InitDocument(doc)
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    cell_label = shape_tool.AddShape(cell_shape)
    TDataStd_Name.Set_s(cell_label, TCollection_ExtendedString("GyrCell"))

    root_label = shape_tool.NewShape()
    TDataStd_Name.Set_s(root_label, TCollection_ExtendedString("GyrArray"))

    for ix in range(n_xy):
        for iy in range(n_xy):
            for iz in range(n_z):
                trsf = gp_Trsf()
                trsf.SetTranslation(gp_Vec(
                    xy_start + ix * a,
                    xy_start + iy * a,
                    z_start  + iz * a,
                ))
                shape_tool.AddComponent(root_label, cell_label, TopLoc_Location(trsf))

    print(f"[OK] {total_inst} instances placed ({time.time() - t0:.1f}s)")
    sys.stdout.flush()

    if inc_duct:
        print("[INFO] (3/4) Building duct wall (B-rep solid)...")
        sys.stdout.flush()
        t0 = time.time()
        try:
            wall_shape = _make_duct_wall_ocp()
            wall_label = shape_tool.AddShape(wall_shape)
            TDataStd_Name.Set_s(wall_label, TCollection_ExtendedString("DuctWall"))
            print(f"[OK] Duct wall added ({time.time() - t0:.1f}s)")
        except Exception as e:
            print(f"[WARN] Duct wall failed: {e}")
        sys.stdout.flush()
    else:
        print("[INFO] (3/4) Duct wall skipped")
        sys.stdout.flush()

    shape_tool.UpdateAssemblies()

    print("[INFO] (4/4) Writing ISO 10303-214 (AP214) Assembly STEP...")
    sys.stdout.flush()
    Interface_Static.SetCVal_s("write.step.schema", "AP214")

    t0 = time.time()
    writer = STEPCAFControl_Writer()
    writer.SetColorMode(False)
    writer.SetNameMode(True)

    ok = writer.Transfer(doc)
    if not ok:
        print("[WARN] Transfer returned False (continuing)")

    status = writer.Write(out_path)
    elapsed = time.time() - t0

    if status == 1 and os.path.isfile(out_path):
        size_kb = os.path.getsize(out_path) / 1024
        print(f"[DONE] Assembly STEP saved: {size_kb:.1f} KB ({elapsed:.1f}s)")
        print(f"[INFO] Format: ISO 10303-214 (AP214)")
        print(f"[INFO] Structure: PRODUCT_DEFINITION x1 + "
              f"NEXT_ASSEMBLY_USAGE_OCCURENCE x{total_inst}")
        sys.exit(0)
    else:
        print(f"[ERROR] STEP write failed (status={status})")
        sys.exit(1)


if __name__ == "__main__":
    main()

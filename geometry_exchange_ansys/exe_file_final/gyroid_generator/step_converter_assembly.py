#!/usr/bin/env python3
"""
STEP converter — ISO 10303-214 (AP214) using STEPControl_Writer.

Builds a unit cell mesh, places N instances via Moved() (shared topology),
and writes a single compound with STEPControl_Writer for maximum viewer
compatibility (ANSYS, FreeCAD, eDrawings, etc.).

Usage:
    step_converter_assembly.py <a> <t> <res_cell> <n_xy> <n_z>
                               <z_start> <xy_start> <include_duct> <output.step>
"""
import os
import sys
import tempfile
import time

import numpy as np

DUCT_OUTER = 25.4
DUCT_WALL = 1.0
TOTAL_Z = 110.0


def _make_unit_cell_ocp(a: float, t: float, res: int):
    """Unit cell (a x a x a mm) marching_cubes -> OCP sewed shell."""
    from skimage.measure import marching_cubes
    import trimesh

    n = max(8, int(res))
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

    # Decimate if too many faces (target ~500 for small STEP)
    if len(mesh.faces) > 800:
        try:
            mesh = mesh.simplify_quadric_decimation(500)
        except Exception:
            pass

    tmp = tempfile.mktemp(suffix=".stl")
    mesh.export(tmp, file_type="stl")
    n_faces = len(mesh.faces)

    from OCP.StlAPI import StlAPI_Reader
    from OCP.TopoDS import TopoDS_Shape as _Shape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing

    shape = _Shape()
    if not StlAPI_Reader().Read(shape, tmp):
        os.remove(tmp)
        raise RuntimeError("StlAPI_Reader failed")
    os.remove(tmp)

    sew = BRepBuilderAPI_Sewing(sp * 0.1)
    sew.Add(shape)
    sew.Perform()
    result = sew.SewedShape()
    if result.IsNull():
        raise RuntimeError("Sewing returned null")
    return result, n_faces


def _make_duct_wall_ocp():
    """Duct wall = outer box - inner box -> B-rep solid."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Pnt

    outer = BRepPrimAPI_MakeBox(
        gp_Pnt(0, 0, 0), gp_Pnt(DUCT_OUTER, DUCT_OUTER, TOTAL_Z)
    ).Shape()
    inner = BRepPrimAPI_MakeBox(
        gp_Pnt(DUCT_WALL, DUCT_WALL, 0),
        gp_Pnt(DUCT_OUTER - DUCT_WALL, DUCT_OUTER - DUCT_WALL, TOTAL_Z),
    ).Shape()
    cut = BRepAlgoAPI_Cut(outer, inner)
    cut.Build()
    if not cut.IsDone():
        raise RuntimeError("Duct wall cut failed")
    return cut.Shape()


def main() -> None:
    if len(sys.argv) != 10:
        print(f"[ERROR] Need 9 args, got {len(sys.argv) - 1}")
        sys.exit(1)

    a = float(sys.argv[1])
    t = float(sys.argv[2])
    res_cell = int(sys.argv[3])
    n_xy = int(sys.argv[4])
    n_z = int(sys.argv[5])
    z_start = float(sys.argv[6])
    xy_start = float(sys.argv[7])
    inc_duct = sys.argv[8].lower() in ("1", "true", "yes")
    out_path = os.path.abspath(sys.argv[9])

    total_inst = n_xy * n_xy * n_z
    print(f"[INFO] STEP: a={a}mm t={t} res={res_cell} "
          f"grid={n_xy}x{n_xy}x{n_z}={total_inst} inst")
    sys.stdout.flush()

    # ── OCP ──
    print("[INFO] Loading OCP...")
    sys.stdout.flush()
    try:
        from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
        from OCP.Interface import Interface_Static
        from OCP.gp import gp_Trsf, gp_Vec
        from OCP.TopLoc import TopLoc_Location
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound
        print("[OK] OCP loaded")
    except ImportError as e:
        print(f"[ERROR] OCP: {e}")
        sys.exit(1)
    sys.stdout.flush()

    # ── (1/3) Unit cell ──
    print(f"[INFO] (1/3) Unit cell (res={res_cell})...")
    sys.stdout.flush()
    t0 = time.time()
    try:
        cell_shape, n_cell_faces = _make_unit_cell_ocp(a, t, res_cell)
    except Exception as e:
        print(f"[ERROR] Cell failed: {e}")
        sys.exit(1)
    print(f"[OK] Cell: {n_cell_faces} faces ({time.time() - t0:.1f}s)")
    sys.stdout.flush()

    # ── (2/3) Compound with Moved() instances ──
    print(f"[INFO] (2/3) Placing {total_inst} instances (Moved)...")
    sys.stdout.flush()
    t0 = time.time()

    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    for ix in range(n_xy):
        for iy in range(n_xy):
            for iz in range(n_z):
                trsf = gp_Trsf()
                trsf.SetTranslation(gp_Vec(
                    xy_start + ix * a,
                    xy_start + iy * a,
                    z_start + iz * a,
                ))
                # Moved() shares underlying topology (TShape) — same geometry, different location
                located = cell_shape.Moved(TopLoc_Location(trsf))
                builder.Add(compound, located)

    # Duct wall
    if inc_duct:
        try:
            wall = _make_duct_wall_ocp()
            builder.Add(compound, wall)
            print("[OK] Duct wall added")
        except Exception as e:
            print(f"[WARN] Duct wall: {e}")
    sys.stdout.flush()

    print(f"[OK] Compound built ({time.time() - t0:.1f}s)")
    sys.stdout.flush()

    # ── (3/3) Write STEP AP214 ──
    print("[INFO] (3/3) Writing STEP AP214...")
    sys.stdout.flush()
    Interface_Static.SetCVal_s("write.step.schema", "AP214")

    t0 = time.time()
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    status = writer.Write(out_path)
    elapsed = time.time() - t0

    if status == 1 and os.path.isfile(out_path):
        size_kb = os.path.getsize(out_path) / 1024
        print(f"[DONE] STEP saved: {size_kb:.1f} KB ({elapsed:.1f}s)")
        print(f"[INFO] ISO 10303-214, {total_inst} instances, "
              f"{n_cell_faces} faces/cell")
        sys.exit(0)
    else:
        print(f"[ERROR] Write failed (status={status})")
        sys.exit(1)


if __name__ == "__main__":
    main()

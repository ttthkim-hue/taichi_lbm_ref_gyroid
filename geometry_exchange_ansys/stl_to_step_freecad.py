#!/usr/bin/env freecadcmd
# Convert STL to solid and export STEP. Optional: fuse with duct STEP.
# Usage: set env STL_PATH, STEP_PATH, [DUCT_PATH]; freecadcmd -c "exec(open('stl_to_step_freecad.py').read())"
#   or: freecadcmd stl_to_step_freecad.py <input.stl> <output.step> [duct.step]
import sys
import os

def main():
    if os.environ.get("STL_PATH") and os.environ.get("STEP_PATH"):
        stl_path = os.path.abspath(os.environ["STL_PATH"])
        step_path = os.path.abspath(os.environ["STEP_PATH"])
        duct_path = os.environ.get("DUCT_PATH") or None
        if duct_path:
            duct_path = os.path.abspath(duct_path)
    elif len(sys.argv) >= 3:
        stl_path = os.path.abspath(sys.argv[1])
        step_path = os.path.abspath(sys.argv[2])
        duct_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
    else:
        print("Usage: set STL_PATH, STEP_PATH [, DUCT_PATH] or pass <input.stl> <output.step> [duct.step]", file=sys.stderr)
        sys.exit(1)

    import Mesh
    import Part

    if not os.path.isfile(stl_path):
        print(f"STL not found: {stl_path}", file=sys.stderr)
        sys.exit(1)

    mesh = Mesh.Mesh(stl_path)
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.1)
    shape = shape.removeSplitter()
    try:
        if shape.Shells and len(shape.Shells) >= 1:
            solid = Part.Solid(shape.Shells[0])
        else:
            shell = Part.Shell(shape.Faces)
            solid = Part.Solid(shell)
    except Exception as e:
        print(f"Mesh to solid failed: {e}", file=sys.stderr)
        sys.exit(1)

    if duct_path and os.path.isfile(duct_path):
        duct_shape = Part.Shape()
        duct_shape.read(duct_path)
        result = solid.fuse(duct_shape)
    else:
        result = solid

    Part.export([result], step_path)
    print(f"Exported: {step_path}")

try:
    main()
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)

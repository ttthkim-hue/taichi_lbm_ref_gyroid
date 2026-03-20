#!/usr/bin/env freecadcmd
# B-Rep empty duct 25.4x25.4x110 mm, wall 1mm, inner 23.4x23.4. Export STEP.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD
import Part

OUTER_X, OUTER_Y, OUTER_Z = 25.4, 25.4, 110.0
WALL_MM = 1.0
INNER_XY = 23.4

def main():
    outer = Part.makeBox(OUTER_X, OUTER_Y, OUTER_Z, FreeCAD.Vector(0, 0, 0))
    inner = Part.makeBox(INNER_XY, INNER_XY, OUTER_Z, FreeCAD.Vector(WALL_MM, WALL_MM, 0))
    duct = outer.cut(inner)
    base = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base, "empty_duct_v32.step")
    Part.export([duct], out_path)
    print(f"Exported: {out_path}")
    return 0

# freecadcmd runs script without __name__=="__main__" in some builds
try:
    main()
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)

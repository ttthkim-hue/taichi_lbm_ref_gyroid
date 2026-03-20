#!/usr/bin/env freecadcmd
# B-Rep reference 6x6: 25.4x25.4x110, inlet/outlet buffer 5mm, 36 channels in main.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD
import Part

OUTER_X, OUTER_Y, OUTER_Z = 25.4, 25.4, 110.0
WALL_MM = 1.0
INNER_XY = 23.4
BUF_Z_MM = 5.0
MAIN_Z_START = 5.0
MAIN_Z_LEN = 100.0
WALL_INNER = 1.0
CHANNEL_W = (INNER_XY - 5 * WALL_INNER) / 6
PERIOD = CHANNEL_W + WALL_INNER

def main():
    outer = Part.makeBox(OUTER_X, OUTER_Y, OUTER_Z, FreeCAD.Vector(0, 0, 0))
    # Inlet buffer cavity
    inlet = Part.makeBox(INNER_XY, INNER_XY, BUF_Z_MM + 0.01, FreeCAD.Vector(WALL_MM, WALL_MM, 0))
    outer = outer.cut(inlet)
    # Outlet buffer cavity
    outlet = Part.makeBox(INNER_XY, INNER_XY, BUF_Z_MM + 0.01, FreeCAD.Vector(WALL_MM, WALL_MM, OUTER_Z - BUF_Z_MM - 0.01))
    outer = outer.cut(outlet)
    # 36 channel holes in main
    for kx in range(6):
        for ky in range(6):
            ch = Part.makeBox(CHANNEL_W, CHANNEL_W, MAIN_Z_LEN + 0.01,
                             FreeCAD.Vector(WALL_MM + kx * PERIOD, WALL_MM + ky * PERIOD, MAIN_Z_START))
            outer = outer.cut(ch)
    base = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base, "reference_6x6_v32.step")
    Part.export([outer], out_path)
    print(f"Exported: {out_path}")
    return 0

try:
    main()
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)

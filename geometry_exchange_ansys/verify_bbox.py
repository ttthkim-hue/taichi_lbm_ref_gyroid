#!/usr/bin/env python3
# Verify presence and nominal bbox of STEP files (25.4 x 25.4 x 110 mm).
# Optional: run with FreeCAD to get actual bbox: see README_ANSYS_DELIVERY.md.
import sys
import os

def main():
    base = os.environ.get("GEOMETRY_EXCHANGE_DIR", os.path.dirname(os.path.abspath(__file__)))
    step_files = [
        "empty_duct_v32.step",
        "reference_6x6_v32.step",
        "gyroid_network_a5_t03.step",
    ]
    expected = (25.4, 25.4, 110.0)
    all_ok = True
    for name in step_files:
        path = os.path.join(base, name)
        if not os.path.isfile(path):
            print(f"SKIP (not found): {name}")
            all_ok = False
            continue
        size = os.path.getsize(path)
        print(f"{name}: present ({size} bytes), nominal bbox 25.4 x 25.4 x 110 mm")
    print("Expected bbox: 25.4 x 25.4 x 110 mm (verify in ANSYS after import)")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

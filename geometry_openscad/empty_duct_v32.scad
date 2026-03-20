// V3.2 빈 덕트 (Empty Duct)
// [공통] 외부 단면 25.4×25.4 mm, 외벽 1 mm → 내부 23.4×23.4 mm, 전체 길이 110 mm
// 25.4mm 외부 큐브에서 23.4mm 내부 큐브를 빼는 CSG

OUTER_X = 25.4;
OUTER_Y = 25.4;
OUTER_Z = 110.0;
WALL_MM = 1.0;
INNER_XY = 23.4;  // 25.4 - 2*1

difference() {
    cube([OUTER_X, OUTER_Y, OUTER_Z], center = false);
    translate([WALL_MM, WALL_MM, 0])
        cube([INNER_XY, INNER_XY, OUTER_Z], center = false);
}

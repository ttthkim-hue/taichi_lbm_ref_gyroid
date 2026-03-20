// V3.2 레퍼런스 6×6 셀 (Reference 6x6 Cell)
// [공통] 외부 25.4×25.4 mm, 외벽 1 mm, 전체 110 mm
// Inlet Buffer Z=0~5, Main Z=5~105 (100mm, 6×6 채널), Outlet Buffer Z=105~110
// 내벽 1 mm, 23.4 mm 내부를 6×6 채널로 분할

OUTER_X = 25.4;
OUTER_Y = 25.4;
OUTER_Z = 110.0;
WALL_MM = 1.0;
INNER_XY = 23.4;
BUF_Z_MM = 5.0;
MAIN_Z_START = 5.0;
MAIN_Z_LEN   = 100.0;

// 내벽 5개 × 1 mm, 채널 6개 → 채널폭 = (23.4 - 5*1) / 6 = 3.0667
WALL_INNER = 1.0;
CHANNEL_W  = (INNER_XY - 5 * WALL_INNER) / 6;
PERIOD     = CHANNEL_W + WALL_INNER;

difference() {
    cube([OUTER_X, OUTER_Y, OUTER_Z], center = false);
    // Inlet buffer: 23.4×23.4×5 at (1,1,0)
    translate([WALL_MM, WALL_MM, 0])
        cube([INNER_XY, INNER_XY, BUF_Z_MM + 0.01], center = false);
    // Outlet buffer: 23.4×23.4×5 at (1,1,105)
    translate([WALL_MM, WALL_MM, OUTER_Z - BUF_Z_MM - 0.01])
        cube([INNER_XY, INNER_XY, BUF_Z_MM + 0.01], center = false);
    // Main section: 36 채널 구멍 (Z=5~105)
    for (kx = [0 : 5]) {
        for (ky = [0 : 5]) {
            translate([WALL_MM + kx*PERIOD, WALL_MM + ky*PERIOD, MAIN_Z_START])
                cube([CHANNEL_W, CHANNEL_W, MAIN_Z_LEN + 0.01], center = false);
        }
    }
}

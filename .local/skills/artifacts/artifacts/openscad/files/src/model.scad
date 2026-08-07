$fn = 72;

difference() {
  union() {
    cylinder(h = 10, r = 28);
    translate([0, 0, 10]) sphere(r = 20);
  }

  translate([0, 0, -1]) cylinder(h = 32, r = 10);
}

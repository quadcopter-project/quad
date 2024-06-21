$fa = 1;
$fs = 0.2;
$fn = 100;
module tracker_mount_base(nut_side = 10, screw_radius = 4, nut_depth = 3, thickness = 4) {
    translate([0,0,thickness/2])
    cube([40,54,thickness], center = true);
    translate([0,0,thickness-0.001])
    translate([14,0,0])
    cylinder(5,2.5,2.5);
    
}

module hexagon(side, height, center) {
  length = sqrt(3) * side;
  translate_value = center ? [0, 0, 0] :
                             [side, length / 2, height / 2];
  translate(translate_value)
    for (r = [-60, 0, 60])
      rotate([0, 0, r])
        cube([side, length, height], center=true);
}

module screw_hole(screw_radius=0.3,nut_side=0.8,nut_depth = 0.4, screw_depth = 3){
    cylinder(h = screw_depth, r = screw_radius);
    translate([0,0,nut_depth/2])
    hexagon(side=nut_side,height=nut_depth,center=true);
    
}

module mount_module(screw_radius=3.5,nut_side=0.8,nut_depth = 0, screw_depth = 10, thickness= 7) {
    difference(){
        tracker_mount_base();
        translate([0,0,-0.001])
        screw_hole(screw_radius=screw_radius,nut_side=nut_side,nut_depth = nut_depth, screw_depth = screw_depth);
    }
}
mount_module();
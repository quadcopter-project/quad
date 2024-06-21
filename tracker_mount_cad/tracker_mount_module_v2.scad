$fa = 1;
$fs = 0.2;
module flat_cylinder_ring(outer_radius=10, inner_radius=8, thickness=1) {
    difference(){
        cylinder(h=thickness, r = outer_radius, center = false);
        translate([0,0,-0.005])
        cylinder(h=thickness + 0.01, r = inner_radius, center = false);
    }
}



module thin_support_cylinder(radius=1, height=10, center_offset=9) {
    translate([center_offset,0,0])
    cylinder(h=height, r = radius);
}

function half_circle_up(x) = sqrt(1-x^2);
function half_circle_low(x) = -sqrt(1-x^2);

module support_beam_base(hull_sphere_radius=1, center_line_radius=9, half_angle_span=70, base_height = 5) {
    layer_num = 20;
    for (layer_index = [0:1:layer_num])
        translate([0,0,base_height*(layer_index/layer_num)])
        linear_extrude(height=base_height/layer_num + 0.1)
        support_beam_2d(hull_sphere_radius=hull_sphere_radius, center_line_radius=center_line_radius, slice_half_angle_span=half_angle_span-layer_index*(half_angle_span/layer_num));
    
}

module support_beam_2d(hull_sphere_radius=1, center_line_radius=9, slice_half_angle_span=30) {
    n = 40;
    base_upper_coords=[ for (theta=[-slice_half_angle_span+0.5:slice_half_angle_span/n:slice_half_angle_span-0.5]) [(center_line_radius+hull_sphere_radius*half_circle_up(theta/slice_half_angle_span))*cos(theta) - center_line_radius, (center_line_radius+hull_sphere_radius*half_circle_up(theta/slice_half_angle_span))*sin(theta)]];
    base_lower_coords=[ for (theta=[slice_half_angle_span-0.5:-slice_half_angle_span/n:-slice_half_angle_span+0.5]) [(center_line_radius+hull_sphere_radius*half_circle_low(theta/slice_half_angle_span))*cos(theta) - center_line_radius, (center_line_radius+hull_sphere_radius*half_circle_low(theta/slice_half_angle_span))*sin(theta)]];
    
//    base_lower_coords = [for (x=[-1:0.01:1]) [x,half_circle_up(x)]];
     polygon(concat(base_lower_coords,base_upper_coords));
}

module support_beam(disk_outer_radius = 10, disk_inner_radius = 8, beam_radius = 1, beam_height =30, support_angle_span = 30, support_height = 10) {
    thin_support_cylinder(radius=beam_radius, height = beam_height, center_offset = (disk_outer_radius + disk_inner_radius)/2);
    translate([(disk_outer_radius+disk_inner_radius)/2,0,0])
    support_beam_base(hull_sphere_radius=beam_radius, center_line_radius = (disk_outer_radius+disk_inner_radius)/2, half_angle_span=support_angle_span, base_height = support_height);
    translate([(disk_outer_radius+disk_inner_radius)/2,0,beam_height])
    rotate([180,0,0])
    support_beam_base(hull_sphere_radius=beam_radius, center_line_radius = (disk_outer_radius+disk_inner_radius)/2, half_angle_span=support_angle_span, base_height = support_height);
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


//lower disk 
outer_radius = 35;
inner_radius = 26;
thickness = 5;
screw_line_radius = 30;
screw_radius = 1.75;
nut_side = 3.2;
nut_depth = 2.;
screw_depth = 10;

difference(){
flat_cylinder_ring(outer_radius=outer_radius, inner_radius=inner_radius, thickness=thickness);
    for (phi = [-120,0,120])
        rotate([0,0,phi])
        translate([screw_line_radius,0,0])
        rotate([180,0,0])
        translate([0,0,-thickness-0.001])
            screw_hole(screw_radius=screw_radius, nut_side=nut_side,nut_depth=nut_depth,screw_depth=screw_depth);
}

//beam parameter
beam_radius = 3.5;
beam_height =190; 
support_angle_span = 50; 
support_height = 40;
//support_beams 
for (phi = [-60,60,180])
    rotate([0,0,phi])
    support_beam(disk_outer_radius = outer_radius, disk_inner_radius = inner_radius, beam_radius = beam_radius, beam_height = beam_height, support_angle_span = support_angle_span, support_height = support_height);

//upper dosl
translate([0,0,beam_height-thickness])
difference(){
flat_cylinder_ring(outer_radius=outer_radius, inner_radius=inner_radius, thickness=thickness);
    for (phi = [-120,0,120])
        rotate([0,0,phi])
        translate([screw_line_radius,0,0])
        rotate([180,0,0])
        translate([0,0,-thickness-0.0001])
            screw_hole(screw_radius=screw_radius, nut_side=nut_side,nut_depth=nut_depth,screw_depth=screw_depth);
}



use <tracker_mount_only.scad>

translate([14.8,0,80])
rotate([0,90,0])
mount_module();

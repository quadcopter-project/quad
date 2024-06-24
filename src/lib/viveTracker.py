import triad_openvr
import triad_openvr
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from itertools import count
from matplotlib.animation import FuncAnimation
from operator import add

class TrackerSpace:
    # unit in mm 
    tracker_mount_propeller_dist = 0.125
    trackers = [] # number index and object 
    # find number of available trackers 
    def __init__(self):
        self.interface = triad_openvr.triad_openvr()
        for tracker_name in self.interface.object_names['Tracker']:
            self.trackers.append(ViveTracker(tracker_name, self.interface))

    def calibrateGround(self):
    # generate offset values and pass it to all trackers in space 
        height_list = []
        for tracker in self.trackers:
            _, h, _, _, _, _ = self.interface.devices[tracker.name].get_pose_euler()
            height_list.append(h)
        # generate offset 
        h_offset = -min(height_list)-self.tracker_mount_propeller_dist

        # pass on offset 
        for tracker in self.trackers:
            tracker.offset = [0, h_offset, 0, 0, 0, 0]

class ViveTracker:
    name: str = "tracker"
    euler_pos: list = [0,0,0,0,0,0]
    # openvr system api object here 
    offset: list = [0,0,0,0,0,0]
    # labframe = euler_pos + offset
    interface: triad_openvr
    
    def __init__(self, name:str, interface):
        self.interface = interface
        self.name = name

    def updatepos(self):
        self.euler_pos = self.interface.devices[self.name].get_pose_euler()

    def check_existance(self):
        while self.interface.devices[self.name].get_pose_euler() == None:
            print(f"tracker{self.name} offline, manual intervention required")
            ## pauses whole program might not work well with automated arduino code 
            input("input any key after connection")
        return True
    
    def return_lab_coords(self):
        self.check_existance()
        self.updatepos()
        return list(map(add, self.offset, self.euler_pos))

    def return_lab_coords_no_check(self):
        self.updatepos()
        return list(map(add, self.offset, self.euler_pos))








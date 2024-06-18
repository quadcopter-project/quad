from triad_openvr import triad_openvr
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from itertools import count
from matplotlib.animation import FuncAnimation

class TrackerSpace:
    trackedDevices: dict = dict() # number index and object 
    # find number of available trackers 
    def __init__(self):
        self.interface = triad_openvr.triad_openvr()

    def listTrackedDevices(self):
        

    # initialising object 
    # check if interface exist 

    # return coordinate 
    # 3D visualizer function 

class ViveTracker:
    name: string = "tracker"
    accel: list = 
    def __init__(self, name:str):
    


from triad_openvr import triad_openvr
import time
import numpy as np
import matplotlib
#matplotlib.use('GTK4Cairo')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from itertools import count
from matplotlib.animation import FuncAnimation


v = triad_openvr.triad_openvr()

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Set labels and title
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title('Real-time 3D Plot')

# Initialize the plot with a single point
x_vals = []
y_vals = []
z_vals = []

index = count()
# Adjust the view angle

def animate(i):
    ynew, znew, xnew, _, _, _ = v.devices["tracker_1"].get_pose_euler()
    x_vals.append(xnew)
    y_vals.append(ynew)
    z_vals.append(znew)
    ax.cla()

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Real-time 3D Plot')
    ax.plot(x_vals, y_vals, z_vals)

ani = FuncAnimation(fig, animate, interval=100)
plt.show()

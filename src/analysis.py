"""
analysis.py

EXPERIMENTAL METHOD
At present, this is used for analysing the snaptain results using w2_normalisation in utils::processor.

First, a one-minute recording is made with live-snaptain.py. There, we first keep the drone off,
run the script to initialise everything, then after typing in the filename the program will prompt for one to confirm.
At this stage turn the drone on, and wait for it to settle (listen for interference between the blades, and
wait for that to die off.) If the spectrum is still fuzzy, abort. It should look clean with one pronounced peak 
around 750rpm. If this is not the case it is likely the drone has yet to settle down. Also observe the mass. If there's
a large change, but the peak position doesn't follow, that might indicate a problem.

The full Data class, containing all the raw results, are then dumped to the raw/snap folder in the project home page.
We select a file using this script, and the script will:
    1. Calculate proportionality constant (~Cl) at each time from mass and frequency readings.
        At this step, unexpected peaks (outside [725, 800]) are ignored.
    2. Find the mean and average, with which outliers in the list of Cl are removed.
        Outliers here, we define as lying more than 5 stdev away from the mean.
    3. Plot a graph of the processed Cl against time, and output mean and stdev.

DATA FILES
The following naming convention is followed:
    {name}-{YYYY-MM-DD-H-M-S}
Where in {name}, if we are indicating a height, we prepend an h. So a height of 1cm BELOW reference height, has a name h1.
a negative height is currently denoted h_1

Note, that the reference height h0 is 62.5cm relative to the table surface. and the bottom of the drone is a height 68.1cm above table.
"""


from utils import Data
from time import sleep
import processor

import os
import statistics as st
import numpy as np
import matplotlib.pyplot as plt

from tkinter import Tk
from tkinter.filedialog import askopenfilename

def gen_w2_norm_plots(path: str):
    for filename in os.listdir(path):
        name = os.path.join(path, filename)
        if not os.path.isfile(name) or filename.split('.')[-1] != 'json':
            continue
        print(f'plotting {name}')
        fig = os.path.join(path, 'w2-norm-plots', filename.replace('json', 'pdf'))
        processor.w2_norm_plot(name, fig, fl = 680, fr = 820)

def gen_bin_by_w_plot(path: str):
    fig = os.path.join(path, 'bin-plot.pdf')
    processor.bin_by_w_plot(path, np.linspace(700, 810, 7), fig = fig)

def gen_w2_norm_height_plot(path):
    fig = os.path.join(path, 'cl-height.pdf')
    processor.w2_norm_height_plot(path, fig = fig, fl = 680, fr = 820)

def gen_rpm2_lift_plot(path: str):
    fig = os.path.join(path, 'lift-w.pdf')
    fig2 = os.path.join(path, 'cl-height.pdf')
    processor.rpm2_lift_plot(path, fig = fig, fig2 = fig2, rpm_range = [0, 7300])

def gen_3d_plot(path: str):
    fig = os.path.join(path, '3d.pdf')
    processor.rpm_height_3d_plot(path, fig = fig)

if __name__ == '__main__':
    path = '../raw/bf/setup-1/'
    gen_3d_plot(path)

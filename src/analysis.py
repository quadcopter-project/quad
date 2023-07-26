"""
analysis.py

EXPERIMENTAL METHOD
At present, this is used for analysing the snaptain results using w2_normalisation in utils::Processor.

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


from utils import Data, Processor
import matplotlib.pyplot as plt
from time import sleep

import statistics as st
import numpy as np

import os

from tkinter import Tk
from tkinter.filedialog import askopenfilename

def gen_w2_norm_plots():
    raw_dir = '../raw/snap/07-14'
    for filename in os.listdir(raw_dir):
        name = os.path.join(raw_dir, filename)
        if not os.path.isfile(name) or filename.split('.')[-1] != 'json':
            continue
        print(f'plotting {name}')
        fig = os.path.join(raw_dir, 'w2-norm-plots', filename.replace('json', 'pdf'))
        Processor.w2_norm_plot(name, fig, fl = 680, fr = 820)

# TODO: make these paths into variables. Same for above.
def gen_bin_by_w_plot():
    Processor.bin_by_w_plot('../raw/snap/07-14/', np.linspace(700, 810, 7), fig = '../raw/snap/07-14/bin-plot.pdf')

def gen_rpm2_lift_plot():
    Processor.rpm2_lift_plot('../raw/bf/', fig = '../raw/bf/lift-w.pdf', fig2 = '../raw/bf/cl-height.pdf', rpm_range = [0, 7300])

def gen_w2_norm_height_plot():
    Processor.w2_norm_height_plot('../raw/snap/07-14/', fig = '../raw/snap/07-14/cl-height.pdf', fl = 680, fr = 820)

def gen_3d_plot():
    Processor.rpm_height_3d_plot('../raw/bf', fig = '../raw/bf/3d.pdf')

if __name__ == '__main__':
    gen_rpm2_lift_plot()

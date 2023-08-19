"""
analysis.py
"""


from lib.utils import Data
from time import sleep
from lib import processor

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
    # fig = os.path.join(path, 'lift-w.pdf')
    # fig2 = os.path.join(path, 'cl-height.pdf')
    fig = fig2 = None
    processor.rpm2_lift_plot(path, fig = fig, fig2 = fig2)

def gen_3d_plot(path: str):
    fig = os.path.join(path, '3d.pdf')
    processor.rpm_height_3d_plot(path, fig = fig)

if __name__ == '__main__':
    path = '../raw/bf/setup-1/'
    gen_rpm2_lift_plot(path)

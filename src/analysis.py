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

# by default don't save graphs. Uncomment lines below to save them.
fig = fig2 = None


def gen_w2_norm_plots(path: str):
    data_files = processor.get_data_files(path) 
    for name in data_files:
        data = Data()
        data.load(name)
        print(f'plotting {name}')
        # fig = os.path.join(path, 'w2-norm-plots', name.replace('json', 'pdf'))
        processor.w2_norm_plot(data, fig, fl = 680, fr = 820)


def gen_bin_by_w_plot(paths: str|list):
    # fig = os.path.join(path, 'bin-plot.pdf')
    data_list = processor.get_data_list(paths)
    processor.bin_by_w_plot(data_list, np.linspace(700, 810, 7), fig = fig)


def gen_w2_norm_height_plot(paths: str|list):
    # fig = os.path.join(path, 'cl-height.pdf')
    data_list = processor.get_data_list(paths)
    processor.w2_norm_height_plot(data_list, fig = fig, fl = 680, fr = 820)


def gen_rpm2_lift_plot(paths: str|list):
    # fig = os.path.join(path, 'lift-w.pdf')
    # fig2 = os.path.join(path, 'cl-height.pdf')
    data_list = processor.get_data_list(paths)
    processor.rpm2_lift_plot(data_list, fig = fig, fig2 = fig2)


def gen_3d_plot(paths: str|list):
    # fig = os.path.join(path, '3d.pdf')
    data_list = processor.get_data_list(paths)
    processor.rpm_height_3d_plot(data_list, fig = fig)


if __name__ == '__main__':
    path = '../raw/bf/setup-1/'
    # gen_w2_norm_plots('../raw/snap/07-14/')
    gen_rpm2_lift_plot(path)


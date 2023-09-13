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


def gen_lift_rpm2_plot(paths: str|list):
    # fig = os.path.join(path, 'lift-w.pdf')
    data_list = processor.get_data_list(paths)
    processor.lift_rpm2_plot(data_list, fig = fig,avg =True,rpm_range = [0,12000])

def gen_cl_height_plot(paths: str|list):
    # fig = os.path.join(path, 'cl-height.pdf')
    data_list = processor.get_data_list(paths)
    processor.cl_height_plot(data_list, fig = fig,avg =True,fit = False, rpm_range = [0,12000])


def gen_3d_plot(paths: str|list):
    # fig = os.path.join(path, '3d.pdf')
    data_list = processor.get_data_list(paths)
    processor.rpm_height_3d_plot(data_list, fig = fig)

def gen_ln_cl_ln_height_plot(paths: str|list):
    data_list = processor.get_data_list(paths)
    processor.ln_cl_ln_height_plot(data_list, fig=fig,avg =True, offset= 0)

def gen_cl_height_multiple_plot(paths: str|list):
    # choose which sets of data to use using data_choice
    # 0:160mm,4inch
    # 1:240mm,4inch
    # 2:320mm,4inch
    # 3:240mm,4inch,retested
    data_lists = []
    for path in paths:
        data_lists.append(processor.get_data_list(path))
    processor.cl_height_plot_multiple(data_lists,data_choice=[1,3], fig=fig, fit = False,avg=True,model=2)

def test_data_extractor(paths: str|list):
    data_lists = []
    for path in paths:
        data_lists.append(processor.get_data_list(path))
    processor.extractor(data_lists)




if __name__ == '__main__':
    path = ['../raw/bf2/160mm_prop_spacing_4inch_prop'
            ,'../raw/bf2/240mm_prop_spacing_4inch_prop'
            ,'../raw/bf2/320mm_prop_spacing_4inch_prop'
            ,'../raw/bf2/240mm_prop_spacing_4inch_prop_retest'

            ]
    # gen_w2_norm_plots('../raw/snap/07-14/')
    # gen_lift_rpm2_plot(path)
    # gen_3d_plot(path)
    # gen_ln_cl_ln_height_plot(path)
    # gen_cl_height_plot(path)
    # gen_lift_rpm2_plot(path)
    gen_cl_height_multiple_plot(path)
    # test_data_extractor(path)

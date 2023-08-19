"""
processor.py

Not a real CPU, but deals with all scientific analyses and data processing.

Variable names
- name: relpath / abspath to a 'Data' file (json dump).
- fig: relpath / abspath to where the plotted figure is to be saved (OVERWRITES.)
- path: relpath / abspath to a folder where a batch of data files are located.
- fl, fr: the range of frequencies to survey, [fl, fr]. If None then no limit.
"""


import os, scipy
import matplotlib.pyplot as plt
import numpy as np
import statistics as st

from utils import Data
from math import sqrt
from numbers import Number


"""
SNAPTAIN processing functions 
"""
# takes in a Data object, and for each frame, pick the most prominent peak in [fl, fr].
# the lift that frame is then normalised by frequency squared of the picked peak.
# this gives us a coefficient of lift (CL) against time plot.
# CL is then filtered for outliers (1.5 IQR, z = 3).
# return -> (time: list, CL: list)  (filtered)
def w2_normalisation(data: Data, fl:float = None, fr:float = None) -> tuple[list, list]:
    norm_t = list()
    norm_val = list()
    for frame in data.frames:
        for freq in frame.peak_freq:
            # lies outside the specified range
            if not in_range(freq, fl, fr):
                continue

            # match found
            lift = frame.get_total_mass()
            norm_t.append(frame.t)
            norm_val.append(lift / freq**2) 
            # only take first / tallest one
            break

    outlier_indices = outlier_filter(norm_val, z = 3, iqr_factor = 1.5, percentile_limit = 0)
    norm_t = remove_by_indices(norm_t, outlier_indices)
    norm_val = remove_by_indices(norm_val, outlier_indices)

    return norm_t, norm_val


# plot w2_normalisation result for a single Data dump.
def w2_norm_plot(name: str, fig: str = None, fl = None, fr = None):
    plt.ioff()
    plt.clf()
    data = Data()
    data.load(name)

    if data.height is None:
        print(f':w2_norm_plot: data imported from {name} does not have a height defined; Abort.')
        return

    x, y = w2_normalisation(data, fl = fl, fr = fr)

    mean = st.mean(y)
    stdev = st.stdev(y)
    print(f':w2_norm_plot: mean = {mean}, stdev = {stdev}')
    plt.plot(x, y)
    plt.xlabel('time / s')
    plt.ylabel('(lift / w^2) / g s^2')
    plt.title(f'h = ${data.height}$ cm, mean = ${mean:.3} \\pm {stdev:.1}$')
    if fig:
        plt.savefig(fig)
    plt.show()

    # exit cleanly
    plt.clf()


# process all Data files in a path, for each find a mean CL value,
# then plot that against height.
def w2_norm_height_plot(paths: str|list, fig: str = None, fl = None, fr = None):
    plt.ioff()
    plt.clf()
    height = []
    lift_const = []
    lift_const_err = []

    for name in get_data_files(paths):
        data = Data()
        data.load(name)
        if data.height is None:
            print(f':w2_norm_height_plot: file {name} have ill-defined height. Skipped.')
            continue

        print(f':w2_norm_height_plot: processing {name}')
        norm_t, norm_val = w2_normalisation(data, fl, fr)
        height.append(data.height)
        lift_const.append(st.mean(norm_val)) 
        lift_const_err.append(st.stdev(norm_val))

    plt.errorbar(height,
                 lift_const,
                 yerr = lift_const_err,
                 marker = 'x',
                 markersize = 3,
                 ls = '',
                 elinewidth = 1)
    plt.title('Cl against height')
    plt.xlabel('height / cm')
    plt.ylabel('Coefficient of lift / g s^2')
    
    if fig:
        plt.savefig(fig)
    plt.show()
    plt.clf()
    

# bin lift values by frequency ranges.
# endpoints: endpoints for the bin intervals. 
#   [endpoints[0], endpoints[1]) is the interval for the first bin.
#   the list must be sorted.
# return -> (height, bins)
#   for example bin[0] stores lift of all frames whose peak is between endpoints[0] and endpoints[1]
def bin_by_w(data: Data, endpoints: list) -> tuple[float, list]:
    # element-wise comparison
    if (sorted(endpoints) != endpoints).all():
        print('(E) :bin_by_w: the endpoints provided are not sorted. Bins ill-defined.')

    fl = endpoints[0]
    fr = endpoints[-1]
    # the naive [] * n will fail, as it creates copies of the same list
    bins = [list() for i in range(len(endpoints) - 1)] 
    height = data.height
    
    for frame in data.frames:
        for freq in frame.peak_freq:
            if not in_range(freq, fl, fr):
                continue
            # else in range, find which bin the data belongs to
            for i in range(0, len(endpoints) - 1):
                if in_range(freq, endpoints[i], endpoints[i + 1]):
                    bins[i].append(frame.get_total_mass())
                    break
            break

    # if don't include height, we simply lose this piece of info as they aren't part of frames but Data
    return height, bins


# bin the lift values by w and for each bin, plot a scatter plot of lift versus distance.
# different bins distinguished by colour.
def bin_by_w_plot(paths: str|list, endpoints: list, fig: str = None):
    plt.clf()

    bins_list = list()
    height_list = list()

    for name in get_data_files(paths):
        print(f':bin_by_w_plot: Processing {name}')
        data = Data() 
        data.load(name)

        if data.height is None:
            print(':bin_by_w_plot: height in file {filename} is undefined. Skipping.')

        height, bins = bin_by_w(data, endpoints)
        bins_list.append(bins)
        height_list.append(height)

    # O(n^3). So wow...
    # for each particular bin...
    for i in range(0, len(endpoints) - 1):
        print(f':bin_by_w_plot: Processing bin num. {i}')
        d = list() 
        lift = list()
        # for each particular height...
        for j in range(0, len(height_list)):
            bins = bins_list[j][i]
            # there will be empty bins
            if len(bins) >= 2:
                outlier_indices = outlier_filter(bins, z = 3, iqr_factor = 1.5, percentile_limit = 0)
                bins = remove_by_indices(bins, outlier_indices)

            height = height_list[j]
            # take the frames in the correct bin,
            for mass in bins:
                d.append(height)
                lift.append(mass)
        plt.plot(d,
                 lift,
                 ls = '',           # ls: no linestyle.
                 marker = 'x',      # if no marker the points don't show.
                 markersize = 1,
                 alpha = 0.8,
                 label = f'$\\omega \\in \\left[{endpoints[i]:.2}, {endpoints[i + 1]:.2}\\right)$')

        plt.legend(fontsize = 5,
                   ncol = 3,
                   framealpha = 0.5)
        plt.xlabel('distance / cm')
        plt.ylabel('lift / g')
        plt.title('Lift against distance, binned')

    if fig:
        plt.savefig(fig)
    plt.show()

    plt.clf()


"""
BETAFLIGHT processing functions
"""
# Read Data dumps from path, and sort them into batches (height, timestamp) and for each batch, into different rpm.
# heights: height (float) or heights (float) to show in plot. None: all heights.
# rpm_range: lower (rpm_range[0]) and upper (rpm_range[1]) limit for rpm range of interest.
# return -> result_by_batch: dict = (batch -> result_by_rpm), where
#   result_by_rpm: dict = (target_rpm -> frames)
def get_results_by_batch(paths: str|list, heights: Number|list = None, rpm_range: tuple = None) -> dict:
    if isinstance(heights, Number):
        heights = [heights]

    result_by_batch = dict()   # tuple(height, timestamp) -> list(result_by_rpm: dict)
    # for each result_by_rpm: rpm[4] -> list(frames: Frame)
    # group all with the same height into a series, in which group those with the same target into the same point which we do statistics on.
    for name in get_data_files(paths):
        data = Data()
        data.load(name)

        if 'betaflight' not in data.platform:
            print(f':rpm2_lift_plot: Platform mismatch in file {name}: expected "betaflight", got {data.platform}.')
            continue

        height = data.height
        timestamp = data.timestamp
        mean_target_rpm = st.mean(data.target_rpm)
        batch = (height, timestamp)
        
        if heights and height not in heights:
            continue
        if rpm_range and (mean_target_rpm < rpm_range[0] or mean_target_rpm > rpm_range[1]):
            continue
        
        print(f':rpm2_lift_plot: Processing file {name}.')
        # NOTE: uncomment this hack if you want differentiating by timestamp...
        # height = data.timestamp
        if batch not in result_by_batch.keys():
            result_by_batch[batch] = dict()

        result_by_rpm = result_by_batch[batch]  # target_rpm: tuple -> list(frames)
        target = tuple(data.target_rpm)
        if target not in result_by_rpm.keys():
            result_by_rpm[target] = list()

        result_by_rpm[target].extend(data.frames)
    
    for batch, result_by_rpm in result_by_batch.items():
        for target_rpm, frames in result_by_rpm.items():
            rpm = [frame.get_mean_rpm() for frame in frames]
            total_mass = [frame.get_total_mass() for frame in frames]

            outlier_indices_rpm = set(outlier_filter(rpm, z = 3, iqr_factor = 1.5, percentile_limit = 0))
            outlier_indices_mass = set(outlier_filter(total_mass, z = 3, iqr_factor = 1.5, percentile_limit = 0))
            outlier_indices = list(outlier_indices_rpm | outlier_indices_mass)

            result_by_rpm[target_rpm] = remove_by_indices(frames, outlier_indices)

        result_by_batch[batch] = dict(sorted(result_by_rpm.items(),
                                             key = lambda pair:st.mean(pair[0])))

    # sort by heights
    result_by_batch = dict(sorted(result_by_batch.items()))

    return result_by_batch


# calls get_results_by_batch to process data.
# fig: path to save lift against rpm2 plots.
# fig2: path to save CL against height plot.
def rpm2_lift_plot(paths: str|list, heights: Number|list = None, rpm_range: list = None, fig: str = None, fig2: str = None):
    plt.ioff()
    plt.clf()

    result_by_batch = get_results_by_batch(paths, heights, rpm_range)

    # coefficient of lift plot variables
    x_cl, y_cl, yerr_cl = ([] for i in range(3))
        
    # for every series, do:
    for (height, timestamp), result_by_rpm in result_by_batch.items():
        x, y, xerr, yerr = ([] for i in range(4))
        # for each target in the series, do:
        for target_rpm, frames in result_by_rpm.items():
            rpm = [frame.get_mean_rpm() for frame in frames]
            total_mass = [frame.get_total_mass() for frame in frames]

            rpm_mean = st.mean(rpm)
            rpm_stdev = st.stdev(rpm)
            total_mass_mean = st.mean(total_mass)
            total_mass_stdev = st.stdev(total_mass)

            x.append(rpm_mean ** 2)
            xerr.append(rpm_stdev * 2)
            y.append(total_mass_mean)
            yerr.append(total_mass_stdev)

        lines = plt.errorbar(x, y,
                         xerr = xerr,
                         yerr = yerr,
                         ls = '',
                         marker = 'x',
                         markersize = 3,
                         label = f'h = {height} cm',
                         elinewidth = 1)
        # best fit line
        linecolor = lines[0].get_color()
        res = scipy.stats.linregress(x, y)
        yy = [res.slope * xval + res.intercept for xval in x]
        
        x_cl.append(height)
        y_cl.append(res.slope)
        yerr_cl.append(res.stderr)
        
        plt.plot(x, yy, color = linecolor, linewidth = 1)
        
        plt.xlabel('rpm^2 / min^-2')
        plt.ylabel('lift / g')
        plt.legend(ncol = 4, loc = 'upper left', fontsize = 5)
        plt.title('Lift against rpm plot')

    if fig:
        plt.savefig(fig)
    plt.show()
    plt.clf()

    # TODO: TEST
    for i in range(len(x_cl)):
        plt.errorbar(x_cl[i], y_cl[i],
                     yerr = yerr_cl[i],
                     ls = '',
                     marker = 'x',
                     markersize = 3,
                     elinewidth = 1)
    plt.title('Cl against height')
    plt.xlabel('height / cm')
    plt.ylabel('Cl / (g s^2)')
    if fig2:
        plt.savefig(fig2)
    plt.show()
    plt.clf()


# plot lift(z) against RPM(y) and height(x) in 3D.
def rpm_height_3d_plot(paths: str|list, heights: Number|list = None, rpm_range: list = None, fig: str = None):
    plt.ioff()
    
    figure = plt.figure()
    ax = figure.add_subplot(projection = '3d')
    ax.view_init(elev = 2, azim = 3)

    height_x = []
    rpm_y = []
    mass_z = []
        
    results_by_batch = get_results_by_batch(paths, heights, rpm_range)
    for batch, results_by_rpm in results_by_batch.items():
        height, timestamp = batch   # unpack a batch
        # same height, same rpm...
        for target_rpm, frames in results_by_rpm.items():
            rpm = [frame.get_mean_rpm() for frame in frames]
            total_mass = [frame.get_total_mass() for frame in frames]

            rpm_mean = st.mean(rpm)
            rpm_stdev = st.stdev(rpm)
            total_mass_mean = st.mean(total_mass)
            total_mass_stdev = st.stdev(total_mass)

            height_x.append(height)
            rpm_y.append(rpm_mean)
            mass_z.append(total_mass_mean)

    ax.scatter(height_x, rpm_y, mass_z, marker = '^', s=5)
    ax.set_xlabel('Height / cm')
    ax.set_ylabel('RPM / min^-1')
    ax.set_zlabel('Mass / g')
    
    if fig:
        plt.savefig(fig)

    plt.show()
    plt.clf()


"""
LOAD CELL processing functions
"""
# TODO: make this paths behaviour global.
# paths: list of all paths to use to read data files. str: One single path.
# preview_data = True: show every data object before processing them.
# fig1: straight line fit of measured (corrected mass) against accurately determined mass.
# fig2: residue of fit in fig 1.
def mass_calibration_curve(paths: str|list, preview_data: bool = False, fig1: str = None, fig2: str = None):
    plt.ioff()
    plt.clf()

    data_files = get_data_files(paths)

    std_list = list()   # mass from balance readings
    measured_list = list()  # raw measured mass
    corrected_list = list() # measured mass corrected by considering tilt of stand.

    for name in data_files:
        if 'mass' not in name.split('/')[-1]:
            continue

        data = Data()
        data.load(name)

        if preview_data:
            plotter.plot(data)

        # find accurate mass from file name.
        std_list.append(float(name.split('/')[-1].split('_')[0]))

        # find mean total mass with outlier filtered.
        total_mass = data.get_total_mass()
        mass_outlier_ind = outlier_filter(total_mass, z = 3, iqr_factor = 2)
        total_mass = remove_by_indices(total_mass, mass_outlier_ind) 
        measured_list.append(st.mean(total_mass))

        # TODO: generalise this outlier filtering procedure. (multiple lists as arguments)
        accel = data.get_accel_vec()
        accel_outlier_ind = set()
        for i in range(3):
            comp = [a[i] for a in accel]
            # take union, so we don't disturb the data half-way when still
            # identifying the outliers.
            comp_outlier_ind = set(outlier_filter(comp, z = 3, iqr_factor = 2))
            accel_outlier_ind = accel_outlier_ind | comp_outlier_ind

        accel = remove_by_indices(accel, accel_outlier_ind)

        cos_list = [a[2] / sqrt(a[0]**2 + a[1]**2 + a[2]**2) for a in accel]
        corrected_list.append(st.mean(total_mass) / st.mean(cos_list))

    res = scipy.stats.linregress(std_list, corrected_list)
    yy = [res.slope * x + res.intercept for x in std_list]
    print(res.rvalue ** 2)
    print(res)

    diff = [corrected_list[i] - yy[i] for i in range(len(yy))]

    plt.plot(std_list, corrected_list, ls = '', marker = '+')
    plt.plot(std_list, yy)
    if fig1 is not None:
        plt.savefig(fig1)
    plt.show()
    plt.clf()

    plt.plot(std_list, diff, ls = '', marker = '+')
    if fig2 is not None:
        plt.savefig(fig2)
    plt.show()
    plt.clf()


"""
GENERIC processing functions
"""
# filter a list with z-values, IQR and percentile limit.
# if none of these are specified, no values are filtered.
# return -> indices: list. indices of outlier items.
def outlier_filter(x: list, z: float = None, iqr_factor: float = None, percentile_limit: float = 0) -> list:
    if (percentile_limit >= 100
        or (z and z < 0)
        or (iqr_factor and iqr_factor < 0)):
        raise ValueError(':outlier_filter: Invalid statistical parameters supplied.')

    indices = list()
    mean = st.mean(x)
    stdev = st.stdev(x)
    q3, q1 = np.percentile(x, [75, 25])
    iqr = q3 - q1
    percentile_l, percentile_r = np.percentile(x, [0 + percentile_limit, 100 - percentile_limit])
    
    for i in range(len(x)):
        val = x[i]
        # only need to satisfy one of these criteria to be removed.
        if z is not None and stdev and abs(val - mean) / stdev > z:
            indices.append(i)
        elif (iqr_factor is not None
            and (val > q3 + iqr_factor * iqr or val < q1 - iqr_factor * iqr)):
            indices.append(i)
        elif val > percentile_r or val < percentile_l:
            indices.append(i)
        
    return indices 


# remove elements at positions {indices} in list {x}
# return -> filtered list of x
def remove_by_indices(x: list, indices: list) -> list:
    return [x[i] for i in range(len(x)) if i not in indices]


# return if {val} is in [l, r).
# if either l or r is None, that side of the limit is ignored.
# return -> True if in range, False otherwise.
def in_range(val: float, l: float = None, r: float = None) -> bool:
    return (l is None or l < val) and (r is None or val < r)


# get a list of the paths to all the valid files (json) in a folder
# paths: the folder(s) to look at, non-recursive.
# return -> list of paths to valid files.
def get_data_files(paths: str|list) -> list:
    data_files = list() 
    if type(paths) is str:
        paths = [paths]

    for path in paths:
        data_files.extend(
                [os.path.join(path, filename) 
                for filename in os.listdir(path) 
                if os.path.isfile(os.path.join(path, filename))
                and filename.split('.')[-1] == 'json']
                )
    return data_files


# return a list of Data objects loaded from json files in {paths}.
def get_data_list(paths: str|list) -> list:
    data_list = list()
    data_files = get_data_files(paths)
    for name in data_files:
        data = Data()
        data.load(name)
        data_list.append(data)

    return data_list


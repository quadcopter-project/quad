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
from matplotlib import cm
from utils import Data
from math import sqrt
from numbers import Number


"""
GENERIC processing functions
"""
# plot an errorbar plot.
# linreg: perform linear regression and plot line of same color.
# **kwargs will be passed into plt.errorbar().
# useful for e.g. labelling the lines.
def errorbar_plot(x: list, y: list, xerr: list = None, yerr: list = None, linreg: bool = False,marker : str = 'x', **kwargs):
    plt.subplot(2, 1, 1)
    lines = plt.errorbar(x, y,
                         xerr = xerr,
                         yerr = yerr,
                         **kwargs,
                         ls = '',
                         marker = marker,
                         markersize = 3,
                         elinewidth = 1)

    if linreg:
        # best fit line
        linecolor = lines[0].get_color()
        res = scipy.stats.linregress(x, y)
        y_fit = [res.slope * xx + res.intercept for xx in x]
        
        plt.plot(x, y_fit, color = linecolor, linewidth = 1)
        return y_fit

# filter a list with z-values, IQR and percentile limit.
# if none of these are specified, no values are filtered.
# return -> indices: list. indices of outlier items.
def get_outlier_indices(x: list, z: float = None, iqr_factor: float = None, percentile_limit: float = 0) -> list:
    if (percentile_limit >= 100
        or (z and z < 0)
        or (iqr_factor and iqr_factor < 0)):
        raise ValueError(':get_outlier_indices: Invalid statistical parameters supplied.')

    # can't do statistics
    if len(x) < 2:
        return []

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

# axes: list, or potentially list of lists, corresponding to many axes of the same data set.
# no_outlier: a list of indices where we don't attempt to find outliers.
#             Needed for independent variables.
# **kwargs: filtering options, see arguments of get_outlier_indices
# return -> list: modified axes (original 1d/2d form preserved)
def remove_outliers(axes: list, no_outlier: int|list = [], **kwargs) -> list:
    # create shallow copy to avoid altering original
    axes = [el for el in axes]

    # treat single list case first
    if (len(axes) == 0 or isinstance(axes[0], Number)):
        outlier_indices = get_outlier_indices(axes, **kwargs)
        return remove_by_indices(axes, outlier_indices)
    
    # sanity check: must be at least uniform 2D list.
    l = len(axes[0])
    for axis in axes:
        if l != len(axis):
            raise IndexError('(E) remove_outliers: Lists of different lengths supplied.')

    if type(no_outlier) is int:
        no_outlier = [no_outlier]

    outlier_indices = set()
    # find all the outlier indices first
    for i in range(len(axes)):
        if i in no_outlier:
            continue
        outlier_indices = outlier_indices | set(get_outlier_indices(axes[i], **kwargs))

    # remove corresponding elements in each axis.
    for i in range(len(axes)):
        axes[i] = remove_by_indices(axes[i], outlier_indices)

    return axes

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
                [os.path.join(path, name) 
                for name in os.listdir(path) 
                if os.path.isfile(os.path.join(path, name))
                and name.split('.')[-1] == 'json']
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

    norm_t, norm_val = remove_outliers([norm_t, norm_val],
                                       no_outlier = 0,  # t is independent variable
                                       z = 3,
                                       iqr_factor = 1.5,
                                       percentile_limit = 0)
    return norm_t, norm_val

# plot w2_normalisation result for a single Data dump.
def w2_norm_plot(data: Data, fig: str = None, fl = None, fr = None):
    plt.ioff()
    plt.clf()

    if data.height is None:
        print(f':w2_norm_plot: data provided does not have a height defined; Abort.')
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
def w2_norm_height_plot(data_list: list, fig: str = None, fl = None, fr = None):
    plt.ioff()
    plt.clf()
    height = []
    lift_const = []
    lift_const_err = []

    for data in data_list:
        if data.height is None:
            print(f('(W) w2_norm_height_plot: data with timestamp '
                  '{data.timestamp} have ill-defined height.'))
            continue

        print(f':w2_norm_height_plot: processing {data.timestamp}')
        norm_t, norm_val = w2_normalisation(data, fl, fr)
        height.append(data.height)
        lift_const.append(st.mean(norm_val)) 
        lift_const_err.append(st.stdev(norm_val))

    errorbar_plot(height, lift_const,
                  yerr = lift_const_err)

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
# return -> bins: list(list)
#   for example bin[0] stores lift of all frames whose peak is between endpoints[0] and endpoints[1]
def bin_by_w(data: Data, endpoints: list) -> list:
    # element-wise comparison
    if (sorted(endpoints) != endpoints).all():
        print('(E) :bin_by_w: the endpoints provided are not sorted. Bins ill-defined.')

    fl = endpoints[0]
    fr = endpoints[-1]
    # the naive [] * n will fail, as it creates copies of the same list
    bins = [list() for i in range(len(endpoints) - 1)] 
    
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

    return bins

# bin the lift values by w and for each bin, plot a scatter plot of lift versus distance.
# different bins distinguished by colour.
def bin_by_w_plot(data_list: list, endpoints: list, fig: str = None):
    plt.clf()

    # height -> bins 
    bins_by_height = dict()

    for data in data_list:
        print(f':bin_by_w_plot: Processing {data.timestamp}')
        height = data.height

        if height is None:
            print(f'(W) bin_by_w_plot: height in {data.timestamp} is undefined.')
            continue

        bins = bin_by_w(data, endpoints)
        if height not in bins_by_height:
            bins_by_height[height] = bins
        else:
            orig_bins = bins_by_height[height]
            # combine the bins directly, since colouring by bin stops us
            # from differentiating data sets anyway.
            bins_by_height[height] = [orig_bins[i] + bins[i] for i in range(len(bins))]

    # O(n^3). So wow...
    # for each particular bin...
    for i in range(0, len(endpoints) - 1):
        print(f':bin_by_w_plot: Processing bin num. {i}')
        d = list() 
        lift = list()
        # for each particular height...
        for height, bins in bins_by_height.items():
            # n-th bin in bins at this height.
            # can't use 'bin', since that is a python keyword.
            bn = bins[i]
            bn = remove_outliers(bn,
                                 z = 3,
                                 iqr_factor = 1.5,
                                 percentile_limit = 0)

            # take the frames in the correct bin,
            for mass in bn:
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
def get_result_by_batch(data_list: list, heights: Number|list = None, rpm_range: tuple = None) -> dict:
    if isinstance(heights, Number):
        heights = [heights]

    result_by_batch = dict()   # tuple(height, timestamp) -> list(result_by_rpm: dict)
    # for each result_by_rpm: rpm[4] -> list(frames: Frame)
    # group all with the same height into a series, in which group those with the same target into the same point which we do statistics on.
    for data in data_list:
        if 'betaflight' not in data.platform:
            print(f':rpm2_lift_plot: Platform mismatch in file {data.timestamp}: expected "betaflight", got {data.platform}.')
            continue

        height = data.height
        timestamp = data.timestamp
        mean_target_rpm = st.mean(data.target_rpm)
        batch = (height, timestamp)
        
        if heights and height not in heights:
            continue
        if rpm_range and (mean_target_rpm < rpm_range[0] or mean_target_rpm > rpm_range[1]):
            continue
        
        print(f'get_result_by_batch: Processing file {data.timestamp}.')
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

            # filter frames with data in rpm and total_mass
            # [0] at the end extracts filtered frames from the the three-elemnt list.
            result_by_rpm[target_rpm] = remove_outliers([frames, rpm, total_mass],
                                                        no_outlier = 0,
                                                        z = 3,
                                                        iqr_factor = 1.5,
                                                        percentile_limit = 0)[0]

        result_by_batch[batch] = dict(sorted(result_by_rpm.items(),
                                             key = lambda pair:st.mean(pair[0])))

    # sort by heights
    result_by_batch = dict(sorted(result_by_batch.items()))

    return result_by_batch

# calculates parameters for plotting a single line of lift against rpm
# result_by_rpm: dict(target_rpm -> frames)
# avg = True: take time-averaged mean_rpm and total_mass
# rpm_sq = True: give rpm squared results instead of rpm.
# return -> x, y, xerr, yerr
#   where xerr = yerr = [0...] if avg is False.
def lift_rpm(result_by_rpm: dict, avg: bool = True):
    x, y, xerr, yerr = ([] for i in range(4))
    # for each target in the series, do:
    for target_rpm, frames in result_by_rpm.items():
        rpm = [frame.get_mean_rpm() for frame in frames]
        total_mass = [frame.get_total_mass() for frame in frames]

        rpm_mean = st.mean(rpm)
        rpm_stdev = st.stdev(rpm)
        total_mass_mean = st.mean(total_mass)
        total_mass_stdev = st.stdev(total_mass)

        if avg:
            x.append(rpm_mean)
            xerr.append(rpm_stdev)
            y.append(total_mass_mean)
            yerr.append(total_mass_stdev)

        else:
            for i in range(len(rpm)):
                x.append(rpm[i])
                y.append(total_mass[i])
                xerr.append(0)
                yerr.append(0)

    return x, y, xerr, yerr


# calls get_result_by_batch to process data.
# avg = True: take time-averaged mean_rpm and total_mass
# fig: path to save lift against rpm2 plots.
# kwargs: arguments to be passed to get_result_by_batch
def lift_rpm2_plot(data_list: list, avg: bool = True, fig: str = None, **kwargs):
    plt.ioff()
    plt.clf()

    result_by_batch = get_result_by_batch(data_list, **kwargs)

    # for every series, do:
    for (height, timestamp), result_by_rpm in result_by_batch.items():
        x, y, xerr, yerr = lift_rpm(result_by_rpm, avg)
        xerr = [2 * xx * xe for xx, xe in zip(x, xerr)]
        x = [xx ** 2 for xx in x]
        y_fit = errorbar_plot(x, y, xerr, yerr,
                      linreg = True,
                      label = f'h = {height} cm')
        res = [a-b for a,b in zip(y,y_fit)]
        plt.subplot(2, 1, 2)
        plt.plot(x, res, linewidth=1)

    plt.subplot(2,1,1)
    plt.xlabel('rpm^2 / min^-2')
    plt.ylabel('lift / g')
    plt.legend(ncol = 4, loc = 'upper left', fontsize = 5)
    plt.title('Lift against rpm^2 plot')
    plt.subplot(2,1,2)
    plt.xlabel('rpm^2 / min^-2')
    plt.ylabel('residual / g')
    plt.title('residual_of_linear_estimate')

    if fig:
        plt.savefig(fig)
    plt.show()
    plt.clf()

# plot CL, calculated purely from results at each w, against w, for all heights by default.
def cl_w_plot(data_list: list, avg: bool = True, fig: str = None, **kwargs):
    from math import sqrt

    plt.ioff() 
    plt.clf()

    result_by_batch = get_result_by_batch(data_list, **kwargs)

    for (height, timestamp), result_by_rpm in result_by_batch.items():
        x, y, xerr, yerr = lift_rpm(result_by_rpm, avg)

        yerr = [sqrt((ye * 1 / (xx**2)) ** 2
                    + (xe * 2 * yy / (xx**3)) ** 2)
                for xx, yy, xe, ye in zip(x, y, xerr, yerr)]
        y = [y[i] / (x[i] ** 2) for i in range(len(x))] # CL

        errorbar_plot(x, y,
                      xerr, yerr,
                      linreg = False,
                      label = f'h = {height}cm')

    plt.xlabel('rpm / min ^ -1')
    plt.ylabel('CL / (g s^2)')
    plt.legend(ncol = 4, loc = 'upper left', fontsize = 8)
    plt.title('CL against rpm plot')

    if fig:
        plt.savefig(fig)

    plt.show()
    plt.clf()

# plot a graph of CL (coefficient of lift) against height.
# avg = True: take time-average of mean_rpm and total_mass.
def cl_height_plot(data_list: list, avg: bool = True,fit: bool = True, fig: str = None, **kwargs):
    plt.ioff()
    plt.clf()
    result_by_batch = get_result_by_batch(data_list, **kwargs)

    # cl: coefficient of lift
    x_cl, y_cl, yerr_cl = ([] for i in range(3))

    for (height, timestamp), result_by_rpm in result_by_batch.items():
        x, y, xerr, yerr = lift_rpm(result_by_rpm, avg)
        x = [xx ** 2 for xx in x]

        res = scipy.stats.linregress(x, y)
        x_cl.append(height)
        y_cl.append(res.slope)
        yerr_cl.append(res.stderr)
     
    for i in range(len(x_cl)):
        errorbar_plot(x_cl[i], y_cl[i], yerr = yerr_cl[i])

    plt.title('CL against height')
    plt.xlabel('height / cm')
    plt.ylabel('CL / (g s^2)')

    # fit using the assumption that ground effect behaves as the eqn
    # values of height (x) are made non dimensional by dividing by prop_spacing

    if (fit == True) :
        prop_spacing = 16

        def ground_effect(x,c1,c2,c3):
            c0 =0
            c4 =3
            return np.piecewise(x,[x < c0, x >= c0], [lambda x: c1/(np.power((c0+c4)/prop_spacing,c3))+c2, lambda x: c1/(np.power((x+c4)/prop_spacing,c3))+c2])

        def pipe_effect(x, c5, c6,c7):
            return np.piecewise(x, [x < 0, x >= 0], [lambda x: 0, lambda x: -c5 * (x/prop_spacing) / (np.power(c7, x/prop_spacing*c6))])


        def overall_effect(x,a1,a2,a3,e1,e2):
            return(a1*(1+np.power((x/a2),e1))*(1/(1+np.power((x/a3),e2))))

        fit , cov = scipy.optimize.curve_fit(overall_effect,x_cl,y_cl,p0 = np.asarray([1,3,50,-1,-1]),maxfev = 10000)

        plt.subplot(2,1,1)
        x_ref = np.linspace(min(x_cl), max(x_cl), 1000)
        plt.plot(x_ref,overall_effect(x_ref,*fit))
        overall_residual = [a-b for a,b in zip(y_cl, [overall_effect(a,*fit) for a in x_cl])]
        plt.subplot(2,1,2)
        plt.plot(x_cl,overall_residual)
        plt.plot(x_ref,np.zeros(len(x_ref)))
        print(fit)

    # try a range of C4, calculate the residuals of optimal fits with a given C4
    # a reasonable c4 value is 3
    '''
    
    c4_fit = []
    c4_res = []
    c4_list = []
    for i in range(0,500):
        c4 = i/50
        fit_temp, cov_temp = scipy.optimize.curve_fit(ground_effect,x_cl,y_cl,p0 = np.asarray([4e-6, 2.3e-6, 1]),maxfev = 10000)
        c4_fit.append(fit_temp)
        c4_res.append(sum([a-b for a,b in zip(y_cl, [ground_effect(a,*fit_temp) for a in x_cl])]))
        c4_list.append(c4)
    plt.subplot(2,1,2)
    plt.plot(c4_list,c4_res)
    '''
    # code used to fit ground effect first and then pipe effect
    '''
    fit_ground, e_ground = scipy.optimize.curve_fit(ground_effect,x_cl,y_cl,p0 = np.asarray([4e-6, 2.3e-6, 1]),maxfev = 10000)
    x_ref = np.linspace(min(x_cl), max(x_cl), 1000)

    #plot both the initial value curve and the optimised curve
    plt.plot(x_ref, ground_effect(x_ref, *p0_ground))
    plt.plot(x_ref, ground_effect(x_ref, *fit_ground))
    print(fit_ground)

    residual_ground = [a-b for a,b in zip(y_cl, [ground_effect(a,*fit_ground) for a in x_cl])]
    # fit residual using pipe effect assuming equation below

    fit_pipe, e_pipe = scipy.optimize.curve_fit(pipe_effect,x_cl,residual_ground,maxfev = 10000)
    '''

    if fig:
        plt.savefig(fig)
    plt.show()
    plt.clf()

# this is function to plot for multiple sets of data and multiple fit functions

def cl_height_plot_multiple(data_lists: list,data_choice:list = [0,2], avg: bool = True,fit: bool = True, fig: str = None, model: int = 1, **kwargs):
    plt.ioff()
    plt.clf()
    multi_data = []

    markers = ['x','o','s','v','^']

    for i in range(len(data_lists)):
        result_by_batches=(get_result_by_batch(data_lists[i], **kwargs))

        # cl: coefficient of lift
        x_cl, y_cl, yerr_cl = ([] for j in range(3))

        for (height, timestamp), result_by_rpm in result_by_batches.items():
            x, y, xerr, yerr = lift_rpm(result_by_rpm, avg)
            x = [xx ** 2 for xx in x]

            res = scipy.stats.linregress(x, y)
            x_cl.append(height)
            if (i==1):
                y_cl.append(res.slope + 2.0713488097364073e-07)
            else:
                y_cl.append(res.slope)
            yerr_cl.append(res.stderr)
        # store multiple sets of data for different drone size
        multi_data.append([x_cl,y_cl,yerr_cl])

        # plot error bar for each datapoint
    for i in data_choice:
        x_cl, y_cl, yerr_cl = multi_data[i]
        for j in range(len(x_cl)):
            errorbar_plot(x_cl[j], y_cl[j], yerr=yerr_cl[j], marker = markers[i])
    plt.subplot(2,1,1)
    plt.title('CL against height')
    plt.xlabel('height / cm')
    plt.ylabel('CL / (g s^2)')

    # fit and plot fitted line for each set of data
    # different models to fit data
    prop_spacings = [16,24,32,24,12]
    prop_radii = [5.08,5.08,5.08,5.08,5.08]

    def model_1(x, a1, a2, a3):
        # multiplicative solution with powers -4 and -2
        a5 = 3
        e1 = -4
        e2 =-2
        return (a1 * (1 + np.power(((x+a5)/ a2), e1)) * (1 / (1 + np.power(((x+a5)/ a3), e2))))


    def model_2(x,T_oge):
        # Sanchez-Cuevas
        Kb = 2
        z = x+2
        term1 = 1 - (prop_radius / (4 * z)) ** 2
        term2 = -prop_radius ** 2 * (z / (prop_spacing ** 2 + 4 * z ** 2) ** (3 / 2))
        term3 = -(prop_radius ** 2 / 2) * (z / (2 * prop_spacing ** 2 + 4 * z ** 2) ** (3 / 2))
        term4 = -2 * prop_radius ** 2 * (z / ((2 ** 0.5 * prop_spacing) ** 2 + 4 * z ** 2) ** (3 / 2) * Kb)
        T_ige = T_oge/(term1+term2+term3+term4)
        return T_ige

    def model_3(x,T_oge,x_offset):
        z = x+x_offset
        T_ige = T_oge*np.power((0.9926+0.03794/(np.power(z/2/prop_radius,2))),2/3)

        return T_ige

    if (fit == True):

        if (model == 1):
            fit_init_1 = [[1e-6, 40, 100],
                          [1e-6, 40, 100],
                          [1e-6, 40, 100],
                          [1e-6, 40, 100],
                          [1e-6, 40, 100],]

            exponents_1 = [[-1, -1],
                           [-1, -1]]

            parameters_1 = []
            covs_1 = []

            for i in range(len(multi_data)):
                x_cl, y_cl, yerr_cl = multi_data[i]
                parameter, cov = scipy.optimize.curve_fit(model_1, x_cl, y_cl, p0=np.asarray(fit_init_1[i]),maxfev=10000)
                parameters_1.append(parameter)
                covs_1.append(cov)
                plt.subplot(2, 1, 1)
                x_ref = np.linspace(min(x_cl), max(x_cl), 1000)
                plt.plot(x_ref, model_1(x_ref, *parameter))
                #plt.plot(x_ref,model_1(x_ref,*fit_init_1[i]))
                overall_residual = [a - b for a, b in zip(y_cl, [model_1(a, *parameter) for a in x_cl])]
                plt.subplot(2, 1, 2)
                plt.plot(x_cl, overall_residual)
                plt.plot(x_ref, np.zeros(len(x_ref)))
            print(parameters_1)

        if(model == 2):
            parameters_2 = []
            covs_2 = []
            for i in range(len(multi_data)):
                prop_spacing = prop_spacings[i]
                prop_radius = prop_radii[i]
                x_cl, y_cl, yerr_cl = multi_data[i]
                parameter,cov = scipy.optimize.curve_fit(model_2,x_cl,y_cl,p0 = np.asarray([2.5e-6]),maxfev=10000)
                parameters_2.append(parameter)
                covs_2.append(cov)
                plt.subplot(2, 1, 1)
                x_ref = np.linspace(min(x_cl), max(x_cl), 1000)
                plt.plot(x_ref, model_2(x_ref, *parameter))
                overall_residual = [a - b for a, b in zip(y_cl, [model_2(a, *parameter) for a in x_cl])]
                plt.subplot(2, 1, 2)
                plt.plot(x_cl, overall_residual)
                plt.plot(x_ref, np.zeros(len(x_ref)))
            print(parameters_2)

        if(model == 3):
            parameters_3 = []
            covs_3 = []
            for i in range(len(multi_data)):
                prop_spacing = prop_spacings[i]
                prop_radius = prop_radii[i]
                x_cl, y_cl, yerr_cl = multi_data[i]
                parameter, cov = scipy.optimize.curve_fit(model_3, x_cl, y_cl, maxfev=10000)
                parameters_3.append(parameter)
                covs_3.append(cov)
                plt.subplot(2, 1, 1)
                x_ref = np.linspace(min(x_cl), max(x_cl), 1000)
                plt.plot(x_ref, model_3(x_ref, *parameter))
                overall_residual = [a - b for a, b in zip(y_cl, [model_3(a, *parameter) for a in x_cl])]
                plt.subplot(2, 1, 2)
                plt.plot(x_cl, overall_residual)
                plt.plot(x_ref, np.zeros(len(x_ref)))
            print(parameters_3)



    if fig:
        plt.savefig(fig)
    plt.show()
    plt.clf()

# offset: amount to ADD TO each CL by, before taking ln/ln.
def ln_cl_ln_height_plot(data_list: list, avg: bool = True, fig: str = None, offset: float = 0, **kwargs):
    from math import log
    from scipy import optimize

    plt.ioff()
    plt.clf()

    result_by_batch = get_result_by_batch(data_list, **kwargs)

    # cl: coefficient of lift
    x_cl, y_cl, yerr_cl = ([] for i in range(3))

    for (height, timestamp), result_by_rpm in result_by_batch.items():
        if height < 0:
            raise ValueError('Negative height found in input: Check if you have corrected for reference height?')

        x, y, xerr, yerr = lift_rpm(result_by_rpm, avg)
        x = [xx ** 2 for xx in x]

        res = scipy.stats.linregress(x, y)
        cl = res.slope

        x_cl.append(log(height))
        y_cl.append(log(cl + offset))
        yerr_cl.append(res.stderr / cl)
     
    for i in range(len(x_cl)):
        errorbar_plot(x_cl[i], y_cl[i]) # can't use linreg as we are plotting individual points.

    plt.title('ln(CL) against ln(height)')
    plt.xlabel('ln(height) / ln(cm)')
    plt.ylabel('ln(CL) / ln(g s^2)')

    #fit ln=ln data using 2 and 3 segments piecewise linear equations
    def piecewise_linear_2(x, x0, y0, k1, k2):
        return np.piecewise(x, [x < x0, x >= x0], [lambda x: k1 * x + y0 - k1 * x0, lambda x: k2 * x + y0 - k2 * x0])
    def piecewise_linear_3(x,x0,y0,x1,y1,k1,k2):
        return np.piecewise(x, [x < x0, (x >= x0) & (x < x1), x>= x1], [lambda x: k1 * x + y0 - k1 * x0, lambda x: (x-x0)/(x1-x0)*(y1-y0) + y0 ,  lambda x: k2 * x + y1 - k2 * x1])

    fit3, e3 = optimize.curve_fit(piecewise_linear_3, x_cl, y_cl,p0=np.asarray([3,-13,4,-13,-0.5,0]))
    fit2, e2 = optimize.curve_fit(piecewise_linear_2, x_cl, y_cl, p0=np.asarray([3.75, -13, -0.5, 0]))
    x_ref = np.linspace(min(x_cl),max(x_cl),1000)
    plt.plot(x_ref, piecewise_linear_3(x_ref, *fit3))
    plt.plot(x_ref, piecewise_linear_2(x_ref, *fit2))
    # calculate residuals
    residual3 = y_cl - piecewise_linear_3(x_cl, *fit3)
    residual2 = y_cl-piecewise_linear_2(x_cl,*fit2)

    plt.subplot(2,1,2)
    plt.plot(x_cl,np.zeros(len(x_cl)))
    plt.plot(x_cl,residual2)
    plt.plot(x_cl,residual3)
    plt.xlabel('ln(height) / ln(cm)')
    plt.ylabel('residual')
    # mean square error
    MSE2 = np.square(residual2).mean()
    MSE3 = np.square(residual3).mean()

    print(f'MSE for 2 segment:{MSE2}')
    print(f'MSE for 3 segment:{MSE3}')

    if fig:
        plt.savefig(fig)
    plt.show()
    plt.clf()

# since most matplotlib 3d plot functions require 2d np array z inputs
# interpolation of x and y are used to form meshgrid
def interpolate_to_create_2d_z(x,y,z):
    from scipy.interpolate import griddata
    xi = np.linspace(min(x), max(x), len(x)*5)
    yi = np.linspace(min(y), max(y), len(y)*5)
    Xi, Yi = np.meshgrid(xi, yi)
    # Interpolate z values onto the regular grid
    Zi = griddata((x, y), z, (Xi, Yi), method='linear')
    return Xi,Yi,Zi

# plot lift(z) against RPM2(y) and height(x) in 3D.
def rpm_height_3d_plot(data_list: list, avg:bool = True, fig: str = None, **kwargs):
    plt.ioff()
    plt.clf()
    ax = plt.figure().add_subplot(projection='3d')
    ax.view_init(elev = 2, azim = 3)

    height_x = []
    rpm_y2 = []
    mass_z = []
        
    result_by_batch = get_result_by_batch(data_list, **kwargs)
    for (height, timestamp), result_by_rpm in result_by_batch.items():
        y, z, yerr, zerr = lift_rpm(result_by_rpm, avg)
        for i in range(len(y)):
            height_x.append(height)
            rpm_y2.append(y[i]**2)
            mass_z.append(z[i])

    Xi,Yi,Zi = interpolate_to_create_2d_z(height_x, rpm_y2, mass_z)

    # wireframe plot
    ax.plot_wireframe(Xi,Yi,Zi,rstride=200, cstride=200, linewidth=2)
    # superpose the 3d surface on the wireframe
    surf = ax.plot_surface(Xi, Yi, Zi, cmap=cm.coolwarm,linewidth=0, antialiased=True, alpha = 0.5)

    ax.set_xlabel('Height / cm')
    ax.set_ylabel('RPM^2 / min^-2')
    ax.set_zlabel('Mass / g')
    
    if fig:
        plt.savefig(fig)

    plt.show()
    plt.clf()

# extract data as a list for further processing
def extractor(data_lists: list,avg:bool = False,**kwargs):
    import csv

    multi_data = []
    prop_spacings = [16, 24, 32, 24, 12]
    prop_radii = [5.08, 5.08, 5.08, 5.08, 5.08]
    test_run = [1,1,1,2,1]
    # note that the second run of the 24cm drone is the correction run

    for i in range(len(data_lists)):
        result_by_batches=(get_result_by_batch(data_lists[i], **kwargs))
        for (height, timestamp), result_by_rpm in result_by_batches.items():
            x,y,xerr,yerr = lift_rpm(result_by_rpm, avg)
            for j in range(len(x)):
                # each list contains in order:
                # rpm in rpm, lift in grams, height in cm, prop spacing in cm, prop radii in cm, test run number
                # more can be added
                multi_data.append([x[j],y[j],height,prop_spacings[i],prop_radii[i],test_run[i]])

    filename = '../raw/bf2/all_data.csv'
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(multi_data)

    print(len(multi_data))
    return multi_data

# interpolate and find the offset between the two runs of the same parameters
# for the two runs of the 24cm drone, the cl in g/rpm^2 is calculated to be less by 2.0713488097364073e-07
def same_parameter_comparison(data_lists: list,**kwargs):

    # assuming 0 has more data than 1
    x_cl = [[], []]
    y_cl = [[], []]
    for i in [0,1]:
        result_by_batch = get_result_by_batch(data_lists[i], **kwargs)
        for (height, timestamp), result_by_rpm in result_by_batch.items():
            x, y, xerr, yerr = lift_rpm(result_by_rpm, avg= True)
            x = [xx ** 2 for xx in x]
            res = scipy.stats.linregress(x, y)
            x_cl[i].append(height)
            y_cl[i].append(res.slope)
    #first row contain the height and second row contain diff in cl
    diff = [[],[]]
    for i in range(len(x_cl[1])):
        if (x_cl[1][i] >= min(x_cl[0]) and x_cl[1][i] <= max(x_cl[0])):
            # directly subtract when matching height found
            if (x_cl[1][i]==x_cl[0][i]):
                diff[0].append(x_cl[1][i])
                diff[1].append(y_cl[1][i]-y_cl[0][i])
            # interpolate when not found
            else:
                lhs_index = x_cl[0].index(max((num for num in x_cl[0] if num < x_cl[1][i]), key=lambda x: x))
                rhs_index = x_cl[0].index(max((num for num in x_cl[0] if num > x_cl[1][i]), key=lambda x: x))
                grad = (y_cl[0][rhs_index]-y_cl[0][lhs_index])/(x_cl[0][rhs_index]-x_cl[0][lhs_index])
                diff[0].append(x_cl[1][i])
                diff[1].append(y_cl[1][i]-(y_cl[0][lhs_index]+grad*(x_cl[1][i]-x_cl[0][lhs_index])))

    plt.plot(diff[0],diff[1])
    plt.plot(diff[0],[np.mean(diff[1])]*len(diff[0]))
    plt.title('diff between the two runs of the 240mm drone')
    plt.xlabel('height / cm')
    plt.ylabel('diff in CL / (g s^2)')
    plt.show()
    print(np.mean(diff[1]))

"""
LOAD CELL processing functions
"""
# paths: list of all paths to use to read data files. str: One single path.
# preview_data = True: show every data object before processing them.
# fig1: straight line fit of measured (corrected mass) against accurately determined mass.
# fig2: residue of fit in fig 1.
# NOTE: this function CANNOT take a data_list input, since it reads the mass from the file name. Unfortunately Data was not built with mass calibration in mind.
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
        accel = data.get_accel_vec()
        accel_by_comp = list(map(list, zip(*accel))) # transpose
        
        # pack to be filtered together
        filtered = remove_outliers([*accel_by_comp, total_mass],
                                   z = 3,
                                   iqr_factor = 1.5)

        accel_by_comp = filtered[:3]
        accel = list(map(list, zip(*accel_by_comp)))
        total_mass = filtered[3]

        measured_list.append(st.mean(total_mass))
        cos_list = [a[2] / sqrt(a[0]**2 + a[1]**2 + a[2]**2) for a in accel]
        corrected_list.append(st.mean(total_mass) / st.mean(cos_list))

    res = scipy.stats.linregress(std_list, corrected_list)
    yy = [res.slope * x + res.intercept for x in std_list]
    print(res.rvalue ** 2)
    print(res)

    diff = [corrected_list[i] - yy[i] for i in range(len(yy))]

    plt.plot(std_list, corrected_list, ls = '', marker = 'x')
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

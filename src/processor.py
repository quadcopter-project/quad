import os, scipy
import matplotlib.pyplot as plt
import numpy as np
import statistics as st

from utils import Data

# returns time and values of the -lift / w^2 (read: omega squared!)
# this value is expected to be proportional to the coefficient of lift, Cl.
# among top 3 peaks, it will only take the tallest in range [fl, fr].
# outliers are filtered, to some extent.
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

    # TODO: right now the outlier parameters are hard-coded.
    outlier_indices = outlier_filter(norm_val, z = 3, iqr_factor = 1.5, percentile_limit = 0)
    norm_t = remove_by_indices(norm_t, outlier_indices)
    norm_val = remove_by_indices(norm_val, outlier_indices)

    return norm_t, norm_val


# takes a file 'name', read the data out of it, then plot data.
# if fig parameter is provided, then the figure is not shown but saved.
# z: standard deviations away to qualify as outlier
def w2_norm_plot(name: str, fig: str = None, fl = None, fr = None):
    # turn off interaction if previously turned on by Plotter
    plt.ioff()
    plt.clf()
    data = Data()
    data.load(name)

    if data.height is None:
        print(f':w2_norm_plot: data imported from {name} does not have a height defined; Abort.')
        return

    # fl, fr to filter out misidentified peaks
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


# plot graph of the w2_norm values against height.
def w2_norm_height_plot(path: str, fig: str = None, fl = None, fr = None):
    plt.ioff()
    plt.clf()
    height = []
    lift_const = []
    lift_const_err = []

    for name in get_data_files(path):
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
    

# bin frames in a data by their w, into bins specified by endpoints.
# for example, endpoints of [a, b, c] will give rise to two bins, [a, b) and [b, c)
# return values: list of lists of frames, bins. The index corresponds to the endpoints:
# bin[i] stores heights whose frames have endpoints endpoints[i], endpoints[i + 1].
def bin_by_w(data: Data, endpoints: list):
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


# get all the data (with height) in a particular path, bin the data by w and for each bin, plot a line of lift versus distance.
# endpoints specify the bins. if fig is provided, the graph will be saved to 'fig' instead of displayed.
def bin_by_w_plot(path: str, endpoints: list, fig: str = None):
    plt.clf()

    bins_list = list()
    height_list = list()

    for name in get_data_files(path):
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


def get_results_by_batch(path: str, heights: float|list = None, rpm_range: list = None) -> dict:
    if type(heights) is float or type(heights) is int:
        heights = [heights]

    result_by_batch = dict()   # height, timestamp: float -> list(result_by_rpm: dict)
    # for each result_by_rpm: rpm[4] -> list(frames: Frame)
    # group all with the same height into a series, in which group those with the same target into the same point which we do statistics on.
    for name in get_data_files(path):
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
        # sort ascending by mean of target_rpm list.
        # result_by_batch[batch] = dict(sorted(result_by_rpm.items(),
        #                                       key = lambda pair:st.mean(pair[0])))
        # NOTE: just to remark that I lost 3hrs+ for the last line, which dereferenced result_by_rpm.
        # I was thinking how the dereferenced frames in the next line could've influenced the thing...
        # well, at least it does mean I still understand basics of OOP. Just bad at debugging :)
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


# plot sets of data. Identify sets from their timestamps.
# if timestamp is None, plot all
def rpm2_lift_plot(path: str, heights: float|list = None, rpm_range: list = None, fig: str = None, fig2: str = None):
    plt.ioff()
    plt.clf()

    result_by_batch = get_results_by_batch(path, heights, rpm_range)

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


def rpm_height_3d_plot(path: str, heights: float|list = None, rpm_range: list = None, fig: str = None):
    plt.ioff()
    
    figure = plt.figure()
    ax = figure.add_subplot(projection = '3d')
    ax.view_init(elev = 2, azim = 3)

    height_x = []
    rpm_y = []
    mass_z = []
        
    results_by_batch = get_results_by_batch(path, heights, rpm_range)
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


# filter a list with three different methods.
# returns a list of the outliers' indices
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
        if z is not None and abs(val - mean) / stdev > z:
            indices.append(i)
        elif (iqr_factor is not None
            and (val > q3 + iqr_factor * iqr or val < q1 - iqr_factor * iqr)):
            indices.append(i)
        elif val > percentile_r or val < percentile_l:
            indices.append(i)
        
    return indices 


# remove elements by a list of indices
def remove_by_indices(x: list, indices: list) -> list:
    return [x[i] for i in range(len(x)) if i not in indices]


# a lenient "in range". If fl/fr is None then assume any value at that side.
def in_range(val: float, l: float = None, r: float = None) -> bool:
    return (l is None or l < val) and (r is None or val < r)


# return the path to the list of valid data files
def get_data_files(path: str) -> list:
    return [os.path.join(path, filename) 
            for filename in os.listdir(path) 
            if os.path.isfile(os.path.join(path, filename))
            and filename.split('.')[-1] == 'json']



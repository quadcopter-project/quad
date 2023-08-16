import lib.ard as ard
import lib.utils as utils
import lib.processor as processor
import time, scipy
from statistics import mean
from math import sqrt
import matplotlib.pyplot as plt
import lib.plotter

graph_types = {(0, 0): 'total_mass'}
plotter = lib.plotter.Plotter(nrows = 1, ncols = 1, graph_types = graph_types)

data_files = processor.get_data_files('mass')
data_files = data_files + processor.get_data_files('mass2')

std_list = list()
measured_list = list()
corrected_list = list()


for name in data_files:
    if 'mass' in name.split('/')[-1]:
        data = utils.Data()
        data.load(name)
        plotter.plot(data)
        input()
        std_list.append(float(name.split('/')[-1].split('_')[0]))
        total_mass = data.get_total_mass()
        outlier_ind = processor.outlier_filter(total_mass, z = 3, iqr_factor = 2)
        total_mass = processor.remove_by_indices(total_mass, outlier_ind) 
        measured_list.append(mean(total_mass))

        accel = data.get_accel_vec()
        cos_list = [a[2] / sqrt(a[0]**2 + a[1]**2 + a[2]**2) for a in accel]
        corrected_list.append(mean(total_mass) / mean(cos_list))

res = scipy.stats.linregress(std_list, corrected_list)
yy = [res.slope * x + res.intercept for x in std_list]
print(res.rvalue ** 2)
print(res)

diff = [corrected_list[i] - yy[i] for i in range(len(yy))]

plt.plot(std_list, corrected_list, ls = '', marker = '+')
plt.plot(std_list, yy)
plt.show()
plt.clf()

plt.plot(std_list, diff, ls = '', marker = '+')
plt.show()


"""
Revised version of Plotter class.
NOTE:   This will BREAK old code, specifically right at the initialiser.
        However legacy code can be rectified with relative ease, by constructing the desired graph_types to pass in. 

plots in a non-blocking manner.
When adding a new plot method, one must modify the following:
    - SUPPORTED: list
    - XLABELS: dict
    - YLABELS: dict
    - TITLES: dict
    - init_(graph_type) function    (if required)
    - update_(graph_type) function  (if required)

    vector plotters must end with _vec for generic functions to recognise them automatically.
    they also don't require an XLABEL or YLABEL.

    plotting vectors by component is handled by _comp functions.
"""

from utils import Data
import matplotlib.pyplot as plt

class Plotter:
    # SUPPORTED graph_type's (private)
    SUPPORTED: list = ['audio', 'freq', 'peak', 'dist',
                       'total_mass', 'mean_rpm',
                       'mass_vec', 'accel_vec',
                       'mass_comp', 'accel_comp']

    XLABELS: dict = {'freq': 'freq / Hz'}
    GENERIC_XLABEL = 'time / s'

    YLABELS: dict = {'audio': '',
                     'freq': '',
                     'mean_rpm': 'rpm / min^-1',
                     'peak': 'freq / Hz',
                     'dist': 'distance / cm',
                     'total_mass': 'mass / g',
                     'mass_comp': 'mass / g',
                     'accel_comp': 'accel / m s^-2'}

    TITLES: dict = {'audio': 'Audio',
                    'freq': 'Freq Spectrum',
                    'mean_rpm': 'Mean RPM',
                    'peak': 'History of Peaks',
                    'dist': 'Distance',
                    'total_mass': 'Total Mass',
                    'mass_vec': 'Mass',
                    'mass_comp': 'Mass by Component',
                    'accel_vec': 'Acceleration',
                    'accel_comp': 'Acceleration by Component'}

    lines: dict = dict() # dictionaries of list of lines


    # INIT functions (private)
    # graph_types: dict = graph_id: Tuple[row, col] -> grahp_type: str in self.SUPPORTED
    def __init__(self, nrows: int, ncols: int, graph_types: dict):
        plt.ion()

        for graph_type in graph_types.values():
            if graph_type not in self.SUPPORTED:
                raise NotImplementedError(f'(E) Plotter:__init__: graph_type "{graph_type}" is not supported.')

        self.nrows = nrows
        self.ncols = ncols
        self.graph_types = graph_types
        self.fig, self.axs = plt.subplots(nrows = nrows, ncols = ncols, squeeze = False, constrained_layout = True)

        for graph_id, graph_type in self.graph_types.items():
            init_func_name = 'init_' + graph_type
            # fallback to generic functions
            if not hasattr(self, init_func_name):
                graph_subtype = graph_type.split('_')[-1]
                match graph_subtype:
                    case 'vec':
                        init_func_name = 'init_generic_vec'
                    case 'comp':
                        init_func_name = 'init_generic_comp'
                    case _:
                        init_func_name = 'init_generic'

            init_func = getattr(self, init_func_name)

            init_func(graph_id, graph_type)
            self.set_labels(graph_id, graph_type) 
    
    def init_freq(self, graph_id: tuple, graph_type: str):
        axis = self.get_axis(graph_id)
        lines = self.get_lines(graph_id)
        lines.append(axis.plot([], [])[0])   # index 0:  frequency spectrum
        lines.append(axis.plot([], [], 'ro')[0]) # index 1: peaks
        
    def init_peak(self, graph_id: tuple, graph_type: str):
        axis = self.get_axis(graph_id)
        lines = self.get_lines(graph_id)
        lines.append(axis.plot([], [], marker='o', ls='', markersize = 2)[0])

    def init_generic(self, graph_id: tuple, graph_type: str):
        axis = self.get_axis(graph_id)
        lines = self.get_lines(graph_id)
        lines.append(axis.plot([], [])[0])

    def init_generic_vec(self, graph_id: tuple, graph_type: str):
        row, col = graph_id
        self.axs[row][col].remove()
        self.axs[row][col] = self.fig.add_subplot(self.nrows, self.ncols,   # the original grid
                                             self.ncols * row + col + 1, projection = '3d') # intended id
        line = self.get_lines(graph_id)
        axis = self.get_axis(graph_id)
        line.append(axis.quiver(0, 0, 0, 0, 0, 0))

    def init_generic_comp(self, graph_id: tuple, graph_type: str):
        axis = self.get_axis(graph_id)
        lines = self.get_lines(graph_id)
        for i in range(3):  # three components of a vector
            lines.append(axis.plot([], [], label = f'$x_{i}$')[0])
        axis.legend(loc = 'upper left')

    def set_labels(self, graph_id: tuple, graph_type: str):
        axis = self.get_axis(graph_id)
        axis.set_title(self.TITLES[graph_type])
        graph_subtype = graph_type.split('_')[-1]
        match graph_subtype:
            case 'vec':
                axis.set_xlabel('x')
                axis.set_ylabel('y')
                axis.set_zlabel('z')
            case _:     # including comp
                if graph_type in self.XLABELS.keys():
                    axis.set_xlabel(self.XLABELS[graph_type])
                else:
                    axis.set_xlabel(self.GENERIC_XLABEL)

                axis.set_ylabel(self.YLABELS[graph_type])

        

    # UPDATE functions (public)
    # window specified how much of the most recent history to show.
    # by how much, we mean the number of entries in time, NOT number of seconds.
    # defaults to None: show all history
    def plot(self, data: Data, window:int=None):
        for graph_id, graph_type in self.graph_types.items():
            update_func_name = 'update_' + graph_type
            # fallback to generic functions
            if not hasattr(self, update_func_name):
                graph_subtype = graph_type.split('_')[-1]
                match graph_subtype:
                    case 'vec':
                        update_func_name = 'update_generic_vec'
                    case 'comp':
                        update_func_name = 'update_generic_comp'
                    case _:
                        update_func_name = 'update_generic'
            
            update_func = getattr(self, update_func_name)
            update_func(graph_id, graph_type, data, window)

        self.refresh()

    def refresh(self):
        for graph_id, graph_type in self.graph_types.items():
            axis = self.get_axis(graph_id)
            if graph_type.split('_')[-1] == 'vec':
                continue    # handled in update_generic_vec
            else:
                axis.relim()
                axis.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()  

    
    # UPDATE functions (private)
    # The window is ignored here.
    def update_audio(self, graph_id: tuple, graph_type: str, data: Data, window: int = None):
        cur_frame = data.get_frame(-1)
        audio = cur_frame.audio
        if audio is None:
            return
        
        cur_t = cur_frame.t
        dt = cur_frame.dt
        t = [cur_t + n * dt for n in range(len(audio))]

        line = self.get_lines(graph_id)[0]
        line.set_xdata(t)
        line.set_ydata(audio)

    def update_freq(self, graph_id: tuple, graph_type: str, data: Data, window: int = None):
        cur_frame = data.get_frame(-1)
        freq = cur_frame.fft_freq
        ampl = cur_frame.fft_ampl
        peak_freq = cur_frame.peak_freq
        peak_ampl = cur_frame.peak_ampl

        lines = self.get_lines(graph_id)
        lines[0].set_xdata(freq)
        lines[0].set_ydata(ampl)
        lines[1].set_xdata(peak_freq)
        lines[1].set_ydata(peak_ampl)
        
    def update_peak(self, graph_id: tuple, graph_type: str, data: Data, window: int = None):
        x = []
        y = []

        t = data.get_t()
        peaks = data.get_peak_freq()
        if window is not None:
            t = t[-window:]
            peaks = peaks[-window:]

        for i in range(len(t)):
            for peak in peaks[i]:
                x.append(t[i])
                y.append(peak)

        line = self.get_lines(graph_id)[0]
        line.set_xdata(x)
        line.set_ydata(y)
        
    def update_generic(self, graph_id: tuple, graph_type: str, data: Data, window: int = None):
        get_func = getattr(data, 'get_' + graph_type)

        t = data.get_t()
        val = get_func()

        if window is not None:
            t = t[-window:]
            val = val[-window:]

        line = self.get_lines(graph_id)[0]
        line.set_xdata(t)
        line.set_ydata(val)
            
    # TODO: get_mass_vec is not implemented in Frame.
    def update_generic_vec(self, graph_id: tuple, graph_type: str, data: Data, window: int = None):
        cur_frame = data.get_frame(-1)
        get_func_name = 'get_' + graph_type
        get_func = getattr(cur_frame, get_func_name) 

        vec = get_func()
        
        axis = self.get_axis(graph_id)
        lines = self.get_lines(graph_id)
        for i in range(len(lines)):
            lines[i].remove()
        lines.clear()

        # this way component lines have same colour as that in a "by-component" plot
        for i in range(3):
            lines.append(axis.quiver(0, 0, 0, *[vec[j] if j == i else 0 for j in range(3)], color = 'green'))
        
        lines.append(axis.quiver(0, 0, 0, *vec))

        lim = max([abs(v) for v in vec]) * 1.5
        axis.set_xlim3d(left = -lim, right = lim)
        axis.set_ylim3d(bottom = -lim, top = lim)
        axis.set_zlim3d(bottom = -lim, top = lim)

    # TODO: get_mass_comp is not implemented in Data.
    def update_generic_comp(self, graph_id: tuple, graph_type: str, data: Data, window: int = None):
        get_func_name = 'get_' + graph_type.replace('comp', 'vec')
        get_func = getattr(data, get_func_name)
       
        t = data.get_t()
        vec_list = get_func()    # list of vectors by time.

        if window is not None:
            t = t[-window:]
            vec_list = vec_list[-window:]

       
        lines = self.get_lines(graph_id)
        for i in range(3):
            lines[i].set_xdata(t)
            lines[i].set_ydata([vec[i] for vec in vec_list])     # i-th component
    
    # GET functions (private)
    def get_axis(self, graph_id: tuple):
        row, col = graph_id
        return self.axs[row][col]
    
    def get_lines(self, graph_id: tuple) -> list:
        if graph_id not in self.lines.keys():
            self.lines[graph_id] = list()
        return self.lines[graph_id]


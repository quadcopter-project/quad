import pyaudio, time, scipy, serial, os, json, dataclasses, copy

from scipy import signal
from threading import Thread
from dataclasses import dataclass, field
from datetime import datetime

import statistics as st
import numpy as np 
import matplotlib.pyplot as plt
import multiprocessing as mp


@dataclass
class Frame:
    t: float = 0
    mass: list = field(default_factory=list) # list of mass readings from different sensors.
    rpm: list = field(default_factory=list) # list of rpm readings from different motors
    audio:list = field(default_factory=list) # list of lists of audio
    dt:float = 0
    fft_freq:list = field(default_factory=list) 
    fft_ampl: list = field(default_factory=list) 
    peak_freq:list = field(default_factory=list) 
    peak_ampl:list = field(default_factory=list) 
    compact:bool = False        # put at the end, so can assume it implicitly.

    # return _copy_ of original frame without audio
    def compactify(self):
        frame_copy = dataclasses.replace(self)
        frame_copy.audio = []     # do not clear, since frame_copy.audio is a shallow copy
        frame_copy.compact = True
        return frame_copy

    # used to recover data from a saved Data json file.
    def update(self, state:dict):
        for key, value in state.items():
            setattr(self, key, value)

    # even when Arduino isn't connected, this will yield 0.
    # TODO: As we progress, might want to change Arduino behaviour to 
    # raising an error if arduino not found.
    def get_total_mass(self):
        return sum(self.mass)

    def get_mean_rpm(self):
        return st.mean(self.rpm)


@dataclass
class Data:
    height: float = None
    target_rpm: list = None
    timestamp: float = None
    platform: str = None
    compact: bool = False
    frames: list = field(default_factory=list)
    
    # tolerance for data not present: those are assumed zero.
    def add(self, t:float, mass:list=[0], rpm:list=[0],
            audio:list=[0], dt:float=1, fl:float=0, fr:float=20000):
        # process peaks
        freq, ampl = Processor.fft(audio, dt, fl, fr)
        peak_freq, peak_ampl = Processor.find_peaks(freq, ampl) 
        peak_freq, peak_ampl = Processor.sort_peaks(peak_freq, peak_ampl)

        self.frames.append(Frame(t = t,
                                 mass = mass,
                                 rpm = rpm,
                                 audio = audio,
                                 dt = dt,
                                 fft_freq = freq,
                                 fft_ampl = ampl,
                                 peak_freq = peak_freq,
                                 peak_ampl = peak_ampl,
                                 compact = False # TODO: for now assume not compact.
                                 # TODO: compact factor might not be useful after all. Consider its removal.
                          )     )
    
    def clear(self):
        self.height = None
        self.frames.clear()

    # TODO: not tested yet
    def compactify(self):
        data_copy = dataclasses.replace(self)
        data_copy.frames = [frame.compactify() for frame in self.frames]
        data_copy.compact = True
        return data_copy

    def get_t(self):
        return [frame.t for frame in self.frames]

    def get_peak_freq(self):
        return [frame.peak_freq for frame in self.frames]

    def get_mass(self):
        return [frame.mass for frame in self.frames]

    def get_total_mass(self):
        return [frame.get_total_mass() for frame in self.frames]

    def get_mean_rpm(self):
        return [frame.get_mean_rpm() for frame in self.frames]

    def dump(self, name: str):
        frames_list = [frame.__dict__ for frame in self.frames]
        # modify the original dict, because json cannot parse our Frame class.
        # data_dict['frames'] = frames_list # NO!!! This will overwrite self.__dict__['frames'].
        # PEP 448 merge operator. {} term will overwrite frames but create new dict.
        data_dict = self.__dict__ | {'frames': frames_list}
        data_json = json.dumps(data_dict, indent = 4)
        if os.path.isfile(name):
            raise IOError(f'(E) Data::dump: {name} already exists.')

        with open(name, 'w') as file:
            file.write(data_json)

    def load(self, name: str):
        if not os.path.isfile(name):
            raise IOError(f'(E) Data::load: {name} does not exist.')

        # that is, some frames already exist.
        if self.frames:
            raise Exception(f'(E) Data::load: frames are already present. Refusing to overwrite.')
        
        # ...but clear nonetheless.
        self.clear()
        with open(name, 'r') as file:
            data_json = file.read()
            data_dict = json.loads(data_json)
            
            for key, value in data_dict.items():
                # frames have been converted and needs to be dealt with separately
                # plus, only set keys that exist.
                if key != 'frames' and key in self.__dict__:
                    setattr(self, key, value)
            
            for frame_dict in data_dict['frames']:
                frame = Frame()
                frame.update(frame_dict)
                self.frames.append(frame)

    # return average and stdev data for total mass over time.
    # if only one data point is provided, stdev is set to 0.
    def get_mass_stat(self) -> tuple[float, float]:
        tot_mass = self.get_total_mass()
        stdev = st.stdev(tot_mass) if len(tot_mass) > 1 else 0
        return st.mean(tot_mass), stdev
    
    def get_log(self, ind:int = None, _t:float = None):
        frame = self.get_frame(ind, _t)
        return [frame.t, frame.get_total_mass(), frame.get_mean_rpm()] + frame.peak_freq

    def get_frame(self, ind:int = None, _t:float = None):
        if (ind and _t):
            raise Exception("Can only get_frame() specifying one of index and time.")
        if ind:
            return self.frames[ind]
        
        if t:
            for frame in self.frames:
                if frame.t > _t:
                    return frame
        return None

    # deprecated in favour of new load function, which enables more sophiscated Data class structures. 
    def _load_frames_list(self, name):
        if not os.path.isfile(name):
            raise IOError(f'(E) Data::load: {name} does not exist.')

        # that is, some frames already exist.
        if self.frames:
            raise Exception(f'(E) Data::load: frames are already present. Refusing to overwrite.')
        
        # ...but clear nonetheless.
        self.clear()
        with open(name, 'r') as file:
            frames_json = file.read()
            frames_list = json.loads(frames_json)
            for frame_dict in frames_list:
                frame = Frame()
                frame.update(frame_dict)
                self.frames.append(frame)

    # convert the now-deprecated frame_list json files to the new format
    @staticmethod
    def _convert_frames_list(directory: str):
        # output to a 'converted' folder
        output_dir = os.path.join(directory, 'converted')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for filename in os.listdir(directory):
            name = os.path.join(directory, filename)
            output_name = os.path.join(output_dir, filename)
            if (not os.path.isfile(name)) or filename.split('.')[-1] != 'json':
                continue

            print(f'converting {name}')
            data = Data()
            data._load_frames_list(name)
            
            if filename[0] == 'h':
                # remove h at front, remove separators, and replace _ with -,
                # which in the file represents the minus sign.
                height = filename.strip('h').split('-')[0].replace('_', '-')
                height = float(height)
                data.height = height
                print(f'extracted height {height}')

            data.dump(output_name)
            data2 = Data()
            data2.load(output_name)

            # compare originally loaded data and newly extracted. True if identical
            print(data2 == data)


# plots in a non-blocking manner.
class Plotter:
    def __init__(self):
        plt.ion()
        self.fig, self.axs = plt.subplots(nrows = 2, ncols = 3)
        self.axs[0][0].set_title('audio')
        self.axs[0][0].set_xlabel('time / s')
        self.audio_ln = self.axs[0][0].plot([], [])[0]

        self.axs[0][1].set_title('frequency')
        self.axs[0][1].set_xlabel('frequency / Hz')
        self.freq_ln = self.axs[0][1].plot([], [])[0]
        self.peak_ln = self.axs[0][1].plot([], [], 'ro')[0]
        
        self.axs[0][2].set_title('RPM')
        self.axs[0][2].set_xlabel('time / s')
        self.rpm_ln = self.axs[0][2].plot([], [])[0]

        self.axs[1][0].set_title('peaks')
        self.axs[1][0].set_xlabel('time / s')
        self.hist_ln = self.axs[1][0].plot([], [], marker='o', ls='')[0]

        self.axs[1][1].set_title('mass')
        self.axs[1][1].set_xlabel('time / s')
        self.mass_ln = self.axs[1][1].plot([], [])[0]

        # reserved line for analysis
        self.rsvd_ln = self.axs[1][2].plot([], [])[0]
        
    # window specified how much of the most recent history to show.
    # by how much, we mean the number of entries in time, NOT number of seconds.
    # defaults to None: show all history
    def plot(self, data: Data, window:int=None):
        cf = data.get_frame(-1) # current frame
        self.update_audio(cf.t, cf.dt, cf.audio)
        self.update_freq(cf.fft_freq, cf.fft_ampl, cf.peak_freq, cf.peak_ampl)
        self.update_peaks(data.get_t(), data.get_peak_freq(), window)
        self.update_rpm(data.get_t(), data.get_mean_rpm(), window)
        self.update_mass(data.get_t(), data.get_total_mass(), window)
        self.refresh()

    def update_audio(self, ct:float, dt, audio):
        time = [ct + n * dt for n in range(len(audio))]
        self.audio_ln.set_xdata(time)
        self.audio_ln.set_ydata(audio)

    def update_freq(self, freq, ampl, peak_freq, peak_ampl):
        self.freq_ln.set_xdata(freq)
        self.freq_ln.set_ydata(ampl)
        self.peak_ln.set_xdata(peak_freq)
        self.peak_ln.set_ydata(peak_ampl)
        
    def update_peaks(self, t:list, peaks:list, window:int=None):
        x = []
        y = []
        # start from the most recent entries
        t = list(reversed(t))
        peaks = list(reversed(peaks))

        for i in range(len(t)):
            if window is not None and i >= window:
                break
            for peak in peaks[i]:
                x.append(t[i])
                y.append(peak)

        self.hist_ln.set_xdata(x)
        self.hist_ln.set_ydata(y)
        
    def update_mass(self, t:list, total_mass:list, window:int=None): 
        t = list(reversed(t))
        total_mass = list(reversed(total_mass))
        if window is not None:
            t = t[0 : window]
            total_mass = total_mass[0 : window]
        self.mass_ln.set_xdata(t)
        self.mass_ln.set_ydata(total_mass)

    def update_rpm(self, t:list, mean_rpm: list, window:int = None):
        t = list(reversed(t))
        mean_rpm = list(reversed(mean_rpm))
        
        if window is not None:
            t = t[0 : window]
            mean_rpm = mean_rpm[0 : window]

        self.rpm_ln.set_xdata(t)
        self.rpm_ln.set_ydata(mean_rpm)

    # update reserved graph: needs to be explitictly called.
    def update_rsvd(self, x: list, y: list):
        self.rsvd_ln.set_xdata(x)
        self.rsvd_ln.set_ydata(y)
        
    def refresh(self):
        for row in self.axs:
            for ax in row:
                ax.relim()
                ax.autoscale_view()

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()  


# NOTE: the pointed microphone will NOT work without the short converter cable
# inserted right into the laptop. The extension cable from amazon is of the same type as that
# on the mic, so we we MUST connect the extension to the mic first, then between that cable and
# our laptop, the converter cable.
class Recorder:
    CHUNK = 1024  # Record in chunks of 1024 samples
    STARTUP_TIME = 3
    SAMPLE_FORMAT = pyaudio.paFloat32
    CHANNELS = 1
    FS = 48000  # Record at 44100 samples per second
    dt = 1 / FS
    DEVICE_INDEX = None

    # print the outputs and their indices.
    # sometimes PyAudio defaults to the wrong device
    # possibly more likely because we are using pipewire.
    # see https://stackoverflow.com/questions/36894315/how-to-select-a-specific-input-device-with-pyaudio
    @staticmethod
    def get_outputs():
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

    def __init__(self, DEVICE_INDEX = None):
        self.pa = pyaudio.PyAudio()

        self.DEVICE_INDEX = DEVICE_INDEX

        # if not specified... attempt to find pipewire device automatically.
        # don't use 'not' keyword in case index is 0
        if self.DEVICE_INDEX is None:
            info = self.pa.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            for i in range (0, numdevices):
                device = self.pa.get_device_info_by_host_api_device_index(0, i)
                if device.get('maxInputChannels') > 0 and 'pipewire' in device.get('name'):
                    self.DEVICE_INDEX = i
                    break

        # not specified, nor is the device found.
        if self.DEVICE_INDEX is None:
            raise Exception('utils:: Recorder: Device "pipewire" not found. Use get_outputs to see output list.')

        self.stream = self.pa.open(format=self.SAMPLE_FORMAT,
                                   channels=self.CHANNELS,
                                   rate=self.FS,
                                   frames_per_buffer=self.CHUNK,
                                   input=True,
                                   input_device_index=self.DEVICE_INDEX)
        self.record(3)
        
    # get raw data; not parsed to avoid overhead during rec.
    def get_chunk(self) -> bytes:
        # Workaround for input overflowed error
        raw_chunk = self.stream.read(self.CHUNK, exception_on_overflow = False)
        return raw_chunk

    @staticmethod
    def parse(raw_audio: bytes) -> list:
        # fromstring is now deprecated
        parsed = np.frombuffer(raw_audio, dtype=np.float32).tolist()
        return parsed
    
    # record for (time) seconds
    def record(self, window: float=1) -> list:
        audio = []
        """ deprecated method: Infers recorded time from sampling rate.
        #   the resulting audio:list will be of the right length, but
        #   the real-world time is longer than that, introducing extra data.
        for i in range(0, int(self.FS / self.CHUNK * window)):
            audio.extend(self.get_chunk())
        """
        # similar to get_avg_masses in Arduino 
        t = time.time()
        raw_audio = self.get_chunk()
        while time.time() - t < window:
            raw_audio = raw_audio + self.get_chunk() 
            
        # do the resource-heavy conversion only at the end
        audio = self.parse(raw_audio)
        return audio        

    def close():
        # Stop and close the stream 
        self.stream.stop_stream()
        self.stream.close()
        # Terminate the PortAudio interface
        self.pa.terminate()


class Arduino:
    conn: bool = False
    line: str = ""

    def __init__(self, port:str = '/dev/ttyACM0', baud = 230400, timeout = 0.1):
        self.connect(port, baud, timeout) 
        self.reset()
        self.thread = Thread(target=self.worker)
        self.thread.start()
        print('Arduino::__init__: initialised.')

    def connect(self, port:str = '/dev/ttyACM0', baud = 230400, timeout = 0.1):
        try:
            self.dev = serial.Serial(port, baud, timeout=timeout)
            self.port = port
            self.baud = baud
            self.conn = True
        except serial.SerialException:
            print(f"Arudino::connect: SerialException: No device found at {port}.")
            self.conn = False

    # TODO: write a safe exit routine as in Drone::rpm_worker.
    def worker(self):
        if not self.conn:
            return

        while True:
            self.line = self.getline(block=True)

    def reset(self):
        if not self.conn:
            return

        self.dev.setDTR(False)
        time.sleep(1)
        self.dev.reset_input_buffer()
        self.dev.setDTR(True)
        for i in range(10):
            self.getline()

    def disconnect(self):
        if not self.conn:
            print("Arduino::disconnect: Not connected")
            return
        
        self.dev.close()
        self.conn = False

    def getline(self, block: bool = False) -> str:
        if not self.conn:
            time.sleep(0.05)
            return ""

        line = self.dev.readline().decode('ascii').strip()
        if block:
            while not line:
                line = self.dev.readline().decode('ascii').strip()

        return line
    
    # only parse when requested - this saves loads of overhead
    def get_mass(self) -> list:
        if not self.conn:
            return []
        line = self.line  # fetch most recent line
        parsed = []
        try:
            parsed = [float(num) for num in line.split(' ')]
        except ValueError:
            print(f"Arduino::get_mass: ValueError: could not parse {line} to numbers.")
        
        return parsed

    # time is given in seconds.
    # returns average reading on each sensor.
    def get_mass_for(self, window: float=1):
        if not self.conn:
            time.sleep(window)
            return [], []

        tt = time.time()
        readings = []
        t = []

        while time.time() - t < window:
            readings.append(self.get_mass)
            t.append(time.time() - tt)
            time.sleep(0.01)

        return t, readings

    # calibrate motor of index ind, when reference mass of ref_mass is put in.
    def calibrate(self, ind: int, ref_mass: float) -> float:
        if not self.conn:
            print('Arduino::calibrate: Device not connected.')
            return 0
        
        input(f'Arduino::calibrate: put mass of {ref_mass} on load cell {ind}: ')
        
        t, readings = get_mass_for(10)
        reading = st.mean(readings[ind])
        factor = reading / ref_mass
        print(f'Arduino::calibrate: mean value is {reading}, suggested factor {factor}.')


# static methods used for data processing. An instance of processor stores no data, so just call the class directly
class Processor:
    # returns time and values of the -lift / w^2 (read: omega squared!)
    # this value is expected to be proportional to the coefficient of lift, Cl.
    # among top 3 peaks, it will only take the tallest in range [fl, fr].
    # outliers are filtered, to some extent.
    @staticmethod
    def w2_normalisation(data: Data, fl:float = None, fr:float = None) -> tuple[list, list]:
        norm_t = list()
        norm_val = list()
        for frame in data.frames:
            for freq in frame.peak_freq:
                # lies outside the specified range
                if not Processor.in_range(freq, fl, fr):
                    continue

                # match found
                lift = frame.get_total_mass()
                norm_t.append(frame.t)
                norm_val.append(lift / freq**2) 
                # only take first / tallest one
                break

        # TODO: right now the outlier parameters are hard-coded.
        outlier_indices = Processor.outlier_filter(norm_val, z = 3, iqr_factor = 1.5, percentile_limit = 0)
        norm_t = Processor.remove_by_indices(norm_t, outlier_indices)
        norm_val = Processor.remove_by_indices(norm_val, outlier_indices)

        return norm_t, norm_val

    # takes a file 'name', read the data out of it, then plot data.
    # if fig parameter is provided, then the figure is not shown but saved.
    # z: standard deviations away to qualify as outlier
    @staticmethod
    def w2_norm_plot(name: str, fig: str = None, fl = None, fr = None):
        # turn off interaction if previously turned on by Plotter
        plt.ioff()
        plt.clf()
        data = Data()
        data.load(name)

        if data.height is None:
            print(f'Processor::w2_norm_plot: data imported from {name} does not have a height defined; Abort.')
            return

        # fl, fr to filter out misidentified peaks
        x, y = Processor.w2_normalisation(data, fl = fl, fr = fr)

        mean = st.mean(y)
        stdev = st.stdev(y)
        print(f'Processor::w2_norm_plot: mean = {mean}, stdev = {stdev}')
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
    @staticmethod
    def w2_norm_height_plot(path: str, fig: str = None, fl = None, fr = None):
        plt.ioff()
        plt.clf()
        height = []
        lift_const = []
        lift_const_err = []

        for name in Processor.get_data_files(path):
            data = Data()
            data.load(name)
            if data.height is None:
                print(f'Processor::w2_norm_height_plot: file {name} have ill-defined height. Skipped.')
                continue

            print(f'Processor::w2_norm_height_plot: processing {name}')
            norm_t, norm_val = Processor.w2_normalisation(data, fl, fr)
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
    @staticmethod
    def bin_by_w(data: Data, endpoints: list):
        # element-wise comparison
        if (sorted(endpoints) != endpoints).all():
            print('(E) Processor::bin_by_w: the endpoints provided are not sorted. Bins ill-defined.')

        fl = endpoints[0]
        fr = endpoints[-1]
        # the naive [] * n will fail, as it creates copies of the same list
        bins = [list() for i in range(len(endpoints) - 1)] 
        height = data.height
        
        for frame in data.frames:
            for freq in frame.peak_freq:
                if not Processor.in_range(freq, fl, fr):
                    continue
                # else in range, find which bin the data belongs to
                for i in range(0, len(endpoints) - 1):
                    if Processor.in_range(freq, endpoints[i], endpoints[i + 1]):
                        bins[i].append(frame.get_total_mass())
                        break
                break

        # if don't include height, we simply lose this piece of info as they aren't part of frames but Data
        return height, bins

    # get all the data (with height) in a particular path, bin the data by w and for each bin, plot a line of lift versus distance.
    # endpoints specify the bins. if fig is provided, the graph will be saved to 'fig' instead of displayed.
    @staticmethod
    def bin_by_w_plot(path: str, endpoints: list, fig: str = None):
        plt.clf()

        bins_list = list()
        height_list = list()

        for name in Processor.get_data_files(path):
            print(f'Processor::bin_by_w_plot: Processing {name}')
            data = Data() 
            data.load(name)

            if data.height is None:
                print('Processor::bin_by_w_plot: height in file {filename} is undefined. Skipping.')

            height, bins = Processor.bin_by_w(data, endpoints)
            bins_list.append(bins)
            height_list.append(height)

        # O(n^3). So wow...
        # for each particular bin...
        for i in range(0, len(endpoints) - 1):
            print(f'Processor::bin_by_w_plot: Processing bin num. {i}')
            d = list() 
            lift = list()
            # for each particular height...
            for j in range(0, len(height_list)):
                bins = bins_list[j][i]
                # there will be empty bins
                if len(bins) >= 2:
                    outlier_indices = Processor.outlier_filter(bins, z = 3, iqr_factor = 1.5, percentile_limit = 0)
                    bins = Processor.remove_by_indices(bins, outlier_indices)

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

    @staticmethod
    def get_results_by_batch(path: str, heights: float|list = None, rpm_range: list = None):
        if type(heights) is float or type(heights) is int:
            heights = [heights]

        result_by_batch = dict()   # height, timestamp: float -> list(result_by_rpm: dict)
        # for each result_by_rpm: rpm[4] -> list(frames: Frame)
        # group all with the same height into a series, in which group those with the same target into the same point which we do statistics on.
        for name in Processor.get_data_files(path):
            data = Data()
            data.load(name)
            if data.platform != 'betaflight':
                print(f'Processor::rpm2_lift_plot: Platform mismatch in file {name}: expected "betaflight", got {data.platform}.')
                continue

            height = data.height
            timestamp = data.timestamp
            mean_target_rpm = st.mean(data.target_rpm)
            batch = (height, timestamp)
            
            if heights and height not in heights:
                continue
            if rpm_range and (mean_target_rpm < rpm_range[0] or mean_target_rpm > rpm_range[1]):
                continue
            
            print(f'Processor::rpm2_lift_plot: Processing file {name}.')
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

                outlier_indices_rpm = set(Processor.outlier_filter(rpm, z = 3, iqr_factor = 1.5, percentile_limit = 0))
                outlier_indices_mass = set(Processor.outlier_filter(total_mass, z = 3, iqr_factor = 1.5, percentile_limit = 0))
                outlier_indices = list(outlier_indices_rpm | outlier_indices_mass)

                result_by_rpm[target_rpm] = Processor.remove_by_indices(frames, outlier_indices)

            result_by_batch[batch] = dict(sorted(result_by_rpm.items(),
                                                 key = lambda pair:st.mean(pair[0])))
 
        # sort by heights
        result_by_batch = dict(sorted(result_by_batch.items()))

        return result_by_batch

    # plot sets of data. Identify sets from their timestamps.
    # if timestamp is None, plot all
    @staticmethod
    def rpm2_lift_plot(path: str, heights: float|list = None, rpm_range: list = None, fig: str = None, fig2: str = None):
        plt.ioff()
        plt.clf()

        result_by_batch = Processor.get_results_by_batch(path, heights, rpm_range)

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

    @staticmethod
    def rpm_height_3d_plot(path: str, heights: float|list = None, rpm_range: list = None, fig: str = None):
        plt.ioff()
        
        figure = plt.figure()
        ax = figure.add_subplot(projection = '3d')
        ax.view_init(elev = 2, azim = 3)

        height_x = []
        rpm_y = []
        mass_z = []
            
        results_by_batch = Processor.get_results_by_batch(path, heights, rpm_range)
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
    @staticmethod
    def outlier_filter(x: list, z: float = None, iqr_factor: float = None, percentile_limit: float = 0) -> list:
        if (percentile_limit >= 100
            or (z and z < 0)
            or (iqr_factor and iqr_factor < 0)):
            raise ValueError('Processor::outlier_filter: Invalid statistical parameters supplied.')

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
    @staticmethod
    def remove_by_indices(x: list, indices: list) -> list:
        return [x[i] for i in range(len(x)) if i not in indices]

    # a lenient "in range". If fl/fr is None then assume any value at that side.
    @staticmethod
    def in_range(val: float, l: float = None, r: float = None) -> bool:
        return (l is None or l < val) and (r is None or val < r)

    @staticmethod
    def fft(audio: list, dt: float, fl:float=0, fr:float=20000) -> tuple[list, list]:
        freq = np.fft.fftfreq(len(audio), d = dt).tolist()
        ampl = np.abs(np.fft.fft(audio)).tolist()
        # left and right indices between fl, ft
        il = ir = None 
        for i in range(len(freq)):
            if il is None and fl < freq[i]:
                il = i
            if ir is None and fr < freq[i]:
                ir = i - 1
        return freq[il:ir], ampl[il:ir]

    # Filter input signal in time space with scipy filter.
    @staticmethod
    def freq_filter(audio:list, cutoff:float) -> list:
        b, a = signal.butter(5, cutoff / (0.5*FS), btype='high', analog = False)  
        return signal.filtfilt(b, a, audio)

    @staticmethod
    def find_peaks(x:list, y:list, prom=30, dist=20, ht=50):
        peaks, _ = signal.find_peaks(y, prominence=prom, distance=dist, height=ht)
        peak_x = [x[peak] for peak in peaks]
        peak_y = [y[peak] for peak in peaks]
        return peak_x, peak_y

    # sort the peaks in descending strength
    @staticmethod
    def sort_peaks(peak_x:list, peak_y:list):
        res = sorted(zip(peak_y, peak_x), reverse = True)
        sorted_x = [el[1] for el in res]
        sorted_y = [el[0] for el in res]
        return sorted_x, sorted_y

    # return the path to the list of valid data files
    @staticmethod
    def get_data_files(path: str) -> list:
        return [os.path.join(path, filename) 
                for filename in os.listdir(path) 
                if os.path.isfile(os.path.join(path, filename))
                and filename.split('.')[-1] == 'json']


if __name__ == '__main__':
    print('utils:: Called as main, executing tests.')

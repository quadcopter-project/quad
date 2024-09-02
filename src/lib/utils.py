import pyaudio, time, scipy, serial, os, json, dataclasses, copy

from scipy import signal
from threading import Thread
from dataclasses import dataclass, field
from datetime import datetime

import statistics as st
import numpy as np 
import matplotlib.pyplot as plt
import multiprocessing as mp


# stores all experimental data at a point in time.
@dataclass
class Frame:
    t: float = 0

    # arduino input: ArdReading can be passed in with asdict.
    accel: list = field(default_factory=list) # list of lists, each inner list represent three components from an accelerometer.
    dist: list = field(default_factory = list) # list of values, each represent reading from a distance sensor.
    mass: list = field(default_factory=list) # list of mass readings from different sensors.

    # drone input
    rpm: list = field(default_factory=list) # list of rpm readings from different motors

    # mic input
    audio:list = field(default_factory=list) # list of lists of audio
    dt:float = 0
    fft_freq:list = field(default_factory=list) 
    fft_ampl: list = field(default_factory=list) 
    peak_freq:list = field(default_factory=list) 
    peak_ampl:list = field(default_factory=list) 

    tracker_pos:list = field(default_factory=list)

    compact:bool = False    # True: the Frame has been rid of audio.

    # return a copy of frame instance without any currently stored audio.
    # useful for saving memory when loading a lot of files with raw audio.
    # return -> compactified frame (frame.compact = True)
    def compactify(self):
        frame_copy = dataclasses.replace(self)
        frame_copy.audio = []     # do not clear, since frame_copy.audio is a shallow copy
        frame_copy.compact = True
        return frame_copy

    # recover data from a saved Data json file.
    # state: dict with keys being Frame attributes and values the attributes' values.
    def update(self, state:dict):
        for key, value in state.items():
            setattr(self, key, value)

    # NOTE: even when Arduino isn't connected, this will yield 0.
    def get_total_mass(self) -> float:
        return sum(self.mass)

    def get_mean_rpm(self) -> float:
        return st.mean(self.rpm)

    # reconstruct 3d force vector from readings of 9-load cell setup.
    # return -> force in 3D [x, y, z].
    def get_mass_vec(self) -> list:
        if len(self.mass) != 9:
            raise IndexError('(E) Frame::get_mass_vec: must have 9 elements for get_mass_vec to work (9-cell setup.)')

        from numpy import sin, cos, pi

        f = np.reshape(self.mass, (3, 3))  # f: force vectors by cell, even though they are in grams
        DEG15 = pi * 15 / 180
        DEG45 = pi * 45 / 180
        DEG75 = pi * 75 / 180

        # right-handed coordinate system.
        # z points upward, x points along middle line towards cells 1-0
        mass_vec = [None for i in range(3)]
        mass_vec[0] = (- sin(DEG45) * f[0, 1] + sin(DEG45) * f[0, 2]
                       + cos(DEG15) * f[1, 1] + cos(DEG75) * f[1, 2]
                       - cos(DEG75) * f[2, 1] - cos(DEG15) * f[2, 2])
        mass_vec[1] = (- cos(DEG45) * f[0, 1] - cos(DEG45) * f[0, 2]
                       - sin(DEG15) * f[1, 1] + sin(DEG75) * f[1, 2]
                       + sin(DEG75) * f[2, 1] - sin(DEG15) * f[2, 2])
        mass_vec[2] = -sum(f[:, 0])   # z-component adds simply
        return mass_vec

    # NOTE: HARDCODING HERE.
    # return -> reading of the first (there's only one) accelerometer [x, y, z].
    def get_accel_vec(self) -> list:
        return self.accel[0]

    # NOTE: HARDCODING HERE.
    # return -> reading of the first (there's only one) ultrasound distance sensor.
    def get_dist(self) -> float:
        return self.dist[0]


# stores all data.
@dataclass
class Data:
    height: float = None
    target_rpm: list = None
    timestamp: float = None
    platform: str = None    # 'snaptain' or 'betaflight' or 'betaflight-2'
    audiofile: str = None
    description: str = None
    compact: bool = False
    frames: list = field(default_factory=list)
    
    # add a frame of data.
    # kwargs: this allows use of **asdict(ardmanager_object.get_reading())
    # keys in kwargs that are not a Frame attr are ignored.
    def add(self, t:float,
            audio:list = None,
            dt:float = None,
            fl:float = 0,
            fr:float = 20000,
            **kwargs):
        # process peaks
        freq, ampl, peak_freq, peak_ampl = [None for i in range(4)]
        if audio and dt:
            freq, ampl = Numerical.fft(audio, dt, fl, fr)
            peak_freq, peak_ampl = Numerical.find_peaks(freq, ampl) 
            peak_freq, peak_ampl = Numerical.sort_peaks(peak_freq, peak_ampl)

        # remove unknown properties in kwargs
        dummy_frame = Frame()   # hasattr doesn't work on a class.
        for kw in list(kwargs.keys()):  # or else, RuntimeError results.
            if not hasattr(dummy_frame, kw):
                kwargs.pop(kw)

        self.frames.append(Frame(t = t,
                                 audio = audio,
                                 dt = dt,
                                 fft_freq = freq,
                                 fft_ampl = ampl,
                                 peak_freq = peak_freq,
                                 peak_ampl = peak_ampl,
                                 compact = False,
                                 **kwargs
                          )     )
    

    # GET functions (public)
    # returns a generic get function, which attempts to provide a list
    # of that variable in the different frames
    def __getattr__(self, attr: str):
        # intended to sub for generic get_* functions only
        if '_' not in attr or attr.split('_')[0] != 'get':
            raise AttributeError('Attribute does not exist.')

        attr_type, var_name = attr.split('_', 1)
        dummy_frame = Frame()

        if not (hasattr(dummy_frame, attr) or hasattr(dummy_frame, var_name)):
            raise AttributeError('Relevant get_* function or variable not found in Frame.')

        def get_func() -> list:
            # test for the get function
            if hasattr(dummy_frame, attr):
                return [getattr(frame, attr)() for frame in self.frames] 

            return [getattr(frame, var_name) for frame in self.frames]

        return get_func

    def get_date(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime('%d/%m/%Y %H:%M:%S')

    # return -> (mean, stdev) for total mass over time.
    # if only one data point is provided, stdev is set to 0.
    def get_mass_stat(self) -> tuple[float, float]:
        tot_mass = self.get_total_mass()
        stdev = st.stdev(tot_mass) if len(tot_mass) > 1 else 0
        return st.mean(tot_mass), stdev

    # return -> frame at index {ind} or first frame with frame.t > t
    #   None in case of no match
    def get_frame(self, ind:int = None, t:float = None) -> Frame:
        if (ind and t):
            raise Exception("Can only get_frame() specifying one of index and time.")

        if ind:
            return self.frames[ind]
        
        if t:
            for frame in self.frames:
                if frame.t > t:
                    return frame

        return None

    def __getitem__(self, key) -> Frame:
        return self.frames[key]

    # AUXILIARY functions (public)
    # re-initialise this instance.
    def clear(self):
        self.height = None
        self.target_rpm = None
        self.timestamp = None
        self.platform = None
        self.description = None
        self.compact: bool = False
    
        self.frames.clear()

    # TODO: not tested yet
    # remove all audio information in all Frames to reduce memory use.
    # return -> compactified copy of data instance (data.compact = True)
    def compactify(self):
        data_copy = dataclasses.replace(self)
        data_copy.frames = [frame.compactify() for frame in self.frames]
        data_copy.compact = True
        return data_copy

    # save this instance to json file at {name}.
    # name: path to json file.
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

    # load this instance with data in saved json file.
    # name: path to json file.
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


    # LEGACY functions (private)
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
    # output files are saved in path/converted/
    # path: folder where frame_list format data files are stored.
    @staticmethod
    def _convert_frames_list(path: str):
        # output to a 'converted' folder
        output_dir = os.path.join(path, 'converted')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for filename in os.listdir(path):
            name = os.path.join(path, filename)
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


# NOTE: DEPRECATED IN FAVOUR OF plotter.py
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
        
    # only function that needs to be called normally.
    # window: number of the most recent frames in data to show.
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

    # update reserved graph #6: needs to be explitictly called.
    def update_rsvd(self, x: list, y: list):
        self.rsvd_ln.set_xdata(x)
        self.rsvd_ln.set_ydata(y)
        
    # reset graph limits, rescale them and refresh GUI.
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
    chunk = 1024  # Record in chunks of 1024 samples
    startup_time = 3
    sample_format = pyaudio.paFloat32
    channels = 1
    fs = 48000  # Record at 44100 samples per second
    dt = 1 / fs
    device_index = None # A default device index

    # PRIVATE METHODS
    # device_name: which device to record from.
    # kwargs: user-specified pyaudio settings.
    # defaults to linux system with pipewire.
    def __init__(self, device_name: str = 'pipewire', **kwargs):
        for kw, val in kwargs:
            # overload the defaults
            if hasattr(self, kw):
                setattr(self, kw, val)

        self.pa = pyaudio.PyAudio()

        # don't use 'not' keyword in case index is 0
        info = self.pa.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range (0, numdevices):
            device = self.pa.get_device_info_by_host_api_device_index(0, i)
            if device.get('maxInputChannels') > 0 and device_name in device.get('name'):
                self.device_index = i
                break

        # not specified, nor is the device found.
        if self.device_index is None:
            raise Exception(f'utils:: Recorder: Device {device_name} not found. Use get_outputs to see output list.')

        self.stream = self.pa.open(format=self.sample_format,
                                   channels=self.channels,
                                   rate=self.fs,
                                   frames_per_buffer=self.chunk,
                                   input=True,
                                   input_device_index=self.device_index,
                                   # still pass it in just in case other pa options are specified
                                   **kwargs)
        self.record(self.startup_time)  # rid of weird junk at start
        
    # get raw data; not parsed to avoid overhead during rec.
    # return -> raw_chunk: bytes
    def get_chunk(self) -> bytes:
        # Workaround for input overflowed error
        raw_chunk = self.stream.read(self.chunk, exception_on_overflow = False)
        return raw_chunk

    # parse raw_audio received from get_chunk to numbers.
    # return -> list of amplitudes in time
    @staticmethod
    def parse(raw_audio: bytes) -> list:
        parsed = np.frombuffer(raw_audio, dtype=np.float32).tolist()
        return parsed

    # PUBLIC METHODS 
    # print audio devices and their indices
    @staticmethod
    def get_outputs():
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
   
    # window: length of recording in seconds
    # return -> list of amplitues by time.
    def record(self, window: float=1) -> list:
        audio = []

        t = time.time()
        raw_audio = self.get_chunk()
        while time.time() - t < window:
            raw_audio = raw_audio + self.get_chunk() 
            
        # do the resource-heavy conversion only at the end
        audio = self.parse(raw_audio)
        return audio        

    # close the stream and terminate PyAudio.
    def close():
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()


class Numerical:
    # audio: list of amplitudes
    # dt: difference in time between two neighbouring audio values.
    # fl, fr: range of frequencies to do fft [fl, fr].
    # return -> freq's and the corresponding amplitudes at the freqs.
    @staticmethod
    def fft(audio: list, dt: float, fl: float = 0, fr: float = 20000) -> tuple[list, list]:
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

    # high-pass filter.
    # audio: list of amplitudes by time.
    # cutoff: cutoff freqeuency for filter (Hz)
    # fs: samples per second of audio. See Recorder.
    # return -> filtered list.
    @staticmethod
    def freq_filter(audio:list, cutoff:float, fs: float) -> list:
        b, a = signal.butter(5, cutoff / (0.5*fs), btype='high', analog = False)  
        return signal.filtfilt(b, a, audio)

    # find peaks in an x-y plot.
    # prom: prominence, dist: distance. ht: height.
    # default values are empirical.
    # see scipy.signal doc for more details.
    # return -> (x, y) coordinate of peaks.
    @staticmethod
    def find_peaks(x:list, y:list, prom=30, dist=20, ht=50) -> tuple[list, list]:
        peaks, _ = signal.find_peaks(y, prominence=prom, distance=dist, height=ht)
        peak_x = [x[peak] for peak in peaks]
        peak_y = [y[peak] for peak in peaks]
        return peak_x, peak_y

    # sort the peaks in descending y values, then x
    # peak_x, peak_y: coordinate of peaks.
    # return -> sorted lists of peak_x, peak_y.
    @staticmethod
    def sort_peaks(peak_x:list, peak_y:list) -> tuple[list, list]:
        res = sorted(zip(peak_y, peak_x), reverse = True)
        sorted_x = [el[1] for el in res]
        sorted_y = [el[0] for el in res]
        return sorted_x, sorted_y

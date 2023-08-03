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

    # Only works on the 9-cell setup.
    def get_mass_vec(self) -> list:
        if len(self.mass) != 9:
            raise IndexError('(E) Frame::get_mass_vec: must have 9 elements for get_mass_vec to work (9-cell setup.)')

        from numpy import sin, cos, pi

        f = np.reshape(self.mass, (3, 3))  # f: force vectors by cell, even though they are in grams
        DEG15 = pi * 15 / 180
        DEG45 = pi * 45 / 180
        DEG75 = pi * 75 / 180

        mass_vec = [None for i in range(3)]
        mass_vec[0] = (- sin(DEG45) * f[0, 1] + sin(DEG45) * f[0, 2]
                       + cos(DEG15) * f[1, 1] + cos(DEG75) * f[1, 2]
                       - cos(DEG75) * f[2, 1] - cos(DEG15) * f[2, 2])
        mass_vec[1] = (- cos(DEG45) * f[0, 1] - cos(DEG45) * F[0, 2]
                       - sin(DEG15) * f[1, 1] + sin(DEG75) * f[1, 2]
                       - sin(DEG75) * f[2, 1] - sin(DEG15) * f[2, 2])
        mass_vec[2] = sum(f[:, 0])   # z-component adds simply
        return mass_vec


@dataclass
class Data:
    height: float = None
    target_rpm: list = None
    timestamp: float = None
    platform: str = None    # 'snaptain' or 'betaflight' or 'betaflight-2.0'
    description: str = None
    compact: bool = False
    frames: list = field(default_factory=list)
    
    # def add(self, t:float, mass:list=[0], rpm:list=[0],
    #        audio:list=[0], dt:float=1, fl:float=0, fr:float=20000):
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

        # useful for e.g. an unpacked ArdReading.
        for kw in kwargs.keys():
            if not hasattr(Frame, kw):
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
    def get_t(self):
        return [frame.t for frame in self.frames]

    def get_peak_freq(self):
        return [frame.peak_freq for frame in self.frames]

    def get_mass(self):
        return [frame.mass for frame in self.frames]

    # only works as intended on the 3-cell setup.
    def get_total_mass(self):
        return [frame.get_total_mass() for frame in self.frames]

    def get_mean_rpm(self):
        return [frame.get_mean_rpm() for frame in self.frames]

    def get_mass_vec(self):
        return [frame.get_mass_vec() for frame in self.frames]

    # NOTE: a dangerous bit of hard coding. frame.accel is returned as a list of lists, representing [x, y, z] of individual sensors.
    def get_accel_vec(self) -> list:
        return [frame.accel[0] for frame in self.frames]

    # NOTE: same as above, a bit of hardcoding.
    def get_dist(self) -> list:
        return [frame.dist[0] for frame in self.frames]

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


    # AUXILIARY functions (public)
    def clear(self):
        self.height = None
        self.target_rpm = None
        self.timestamp = None
        self.platform = None
        self.description = None
        self.compact: bool = False
    
        self.frames.clear()

    # TODO: not tested yet
    def compactify(self):
        data_copy = dataclasses.replace(self)
        data_copy.frames = [frame.compactify() for frame in self.frames]
        data_copy.compact = True
        return data_copy

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


# NOTE: DEPRECATED.
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


class Numerical:
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


if __name__ == '__main__':
    print('utils:: Called as main, executing tests.')

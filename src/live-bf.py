import os, time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from lib import utils, drone

class BFLive:
    def __init__(self, path: str):
        print('BFLive::__init__: initialising.')
        self.path = path
#        self.recorder = utils.Recorder()
        # TODO: workaround
        self.arduino = utils.Arduino(port = '/dev/ttyACM0')
        self.plotter = utils.Plotter()
        self.quad = drone.Drone('../bf-conf/debug/betaflight-configurator/linux64/betaflight-configurator')

        self.t_str = datetime.now().strftime('%m-%d')
        self.timestamp = time.time()    # timestamp acts as a UUID for this set of data

        self.cnt = -1
        for filename in os.listdir(path):
            file = os.path.join(path, filename) 
            if not os.path.isfile(file) or "json" not in filename:
                continue
            try:
                cnt = int(filename.split('.')[-2].split('_')[-1])
                self.cnt = max(self.cnt, cnt) 
            except ValueError:
                print(f'BFLive::__init__: ValueError: Could not parse cnt value in filename {filename}.')
        self.cnt = self.cnt + 1

        print('BFLive::__init__: init complete.')

    def start(self, height: float, rpm_queue: list, rec_t: float, transient:float):
        print('BFLive::start: the following parameters are scheduled for testing.')
        print(f'height: {height}')
        print('rpm_queue:', *rpm_queue, sep = '\n- ')
        input('BFLive::start: confirm: ')

        # record is not responsible for arming, this way we can emergency quit and record won't rearm our drone.
        self.quad.set_arming(True)
        self.quad.set_rpm_worker_on(True)

        for rpm in rpm_queue:
            self.record(height, rpm, rec_t, transient)

        self.quad.set_rpm_worker_on(False)
        self.quad.set_arming(False)

    def record(self, height: float, target_rpm: int|list, rec_t: float, transient:float):
        if type(target_rpm) is int:
            target_rpm = [target_rpm] * self.quad.NUM_OF_MOTORS

        print(f'BFLive::record: preparing for height = {height}, target_rpm = {target_rpm}, rec_t = {rec_t}')
        filename = f'bf_{height}_{target_rpm}_{self.t_str}_{self.cnt}.json'
        file = os.path.join(self.path, filename)
        data = utils.Data(height = height,
                          target_rpm = target_rpm,
                          timestamp = self.timestamp,
                          platform = 'betaflight')
        self.quad.set_rpm(target_rpm)
        time.sleep(transient)

        print(f'BFLive::record: recording started...')
        t = time.time()
        while time.time() - t < rec_t:
#            audio = self.recorder.record(0.5)
            mass = self.arduino.get_mass()
            rpm = self.quad.get_rpm()
            ct = time.time() - t
            data.add(t = ct,
                     mass = mass,
                     rpm = rpm,
#                     audio = audio,
#                     dt = self.recorder.dt,
                     fl = 400,  # TODO: up to debate if this will hold correct.
                     fr = 1000)
            self.plotter.plot(data, window = 20)
        
        print('BFLive::record: dumping raw data.')
        data.dump(file)

    # TODO: TEST THIS.
    def close(self):
        self.quad.set_rpm_worker_on(False)
        self.quad.set_arming(False)

if __name__ == "__main__":
    live = BFLive(path = '../raw/bf/')
    height = float(input('Height: '))
    try:
        live.start(height = height,
                   #rpm_queue = [1500, 3000, 3500, 4000, 4500, 5000] + [5000 + 250 * n for n in range(1, 14)],
                   rpm_queue = [5000] + [5000 + 250 * n for n in range(1, 14)],
                   rec_t = 20,
                   transient = 20)
    except Exception as e:
        print('live-bf:: The following exception was encountered: ')
        print(str(e))
        live.close()

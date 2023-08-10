import time
from lib import ard, utils, plotter
from utils import Data
from dataclasses import asdict

d = {(0, 0): 'mass_vec', (0, 1): 'mass_comp'}

p = plotter.Plotter(1, 2, d)
ardman = ard.ArdManager()
data = Data()

while True:
    reading = ardman.get_reading()
    print(reading)
    data.add(time.time(), **asdict(reading))
    p.plot(data, window = 50)
   # print(data.get_frame(-1).get_mass_vec()) 
    time.sleep(0.5)

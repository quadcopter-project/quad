import time, json, os

from lib import ard
from lib.utils import Data
from statistics import mean, stdev
from dataclasses import dataclass, field, asdict

ardman = ard.ArdManager()

@dataclass
class Results:
    real_mass: list = field(default_factory = list) 
    measured_mass: list = field(default_factory = list)  # list, with three components

    def dump(self, name: str):
        data_json = json.dumps(self.__dict__, indent = 4)
        if os.path.isfile(name):
            raise IOError(f'(E) Results::dump: {name} already exists.')

        with open(name, 'w') as file:
            file.write(data_json)

    def load(self, name: str):
        if not os.path.isfile(name):
            raise IOError(f'(E) Results::load: {name} does not exist.')

        with open(name, 'r') as file:
            data_json = file.read()
            data_dict = json.loads(data_json)
            
            for key, value in data_dict.items():
                # frames have been converted and needs to be dealt with separately
                # plus, only set keys that exist.
                if key in self.__dict__:
                    setattr(self, key, value)
         

if __name__ == '__main__':
    results = Results()
    while True:
        results.real_mass.append(float(input('Enter mass: ')))
        data = Data()
        t = time.time()
        while time.time() - t < 10:
            reading = ardman.get_reading()
            data.add(time.time(), **asdict(reading))
            time.sleep(0.05)
        
        mass_vec_list = data.get_mass_vec()
        mass_vec = list()
        stdev_vec = list()
        for i in range(3):
            mass_vec.append(mean([vec[i] for vec in mass_vec_list]))
            stdev_vec.append(stdev([vec[i] for vec in mass_vec_list]))

        print(mass_vec)
        print(stdev_vec)
        results.measured_mass.append(mass_vec)

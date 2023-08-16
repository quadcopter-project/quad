import lib.ard as ard
from lib.utils import Data
from lib.plotter import Plotter
from time import time, sleep
from dataclasses import asdict

ZERO_T = 20
MASS_T = 75
HYST_T = 20
FOLDER = 'mass2'

if __name__ == '__main__':
    ardman = ard.ArdManager()
    arduino = ardman[3]
    plt = Plotter(nrows = 1, ncols = 1,
                  graph_types = {(0, 0): 'total_mass'})

    while True:
        mass = float(input('mass / g: '))

        input('confirm tare: ')
        ardman[3].tare(block = True)

        """
        t = time()
        data = Data()
        while time() - t < ZERO_T:
            data.add(t = time() - t, **asdict(ardman.get_reading()))     
            print(data.get_frame(-1))
            plt.plot(data)

        data.dump(f'{FOLDER}/{mass}_zero.json')
        """

        input('confirm measurement start: ')
        t = time()
        data = Data()
        while time() - t < MASS_T:
            data.add(t = time() - t, **asdict(ardman.get_reading()))
            print(data.get_frame(-1))
            plt.plot(data)

        data.dump(f'{FOLDER}/{mass}_mass.json')

        """
        input('confirm mass removal:')
        t = time()
        data = Data()
        while time() - t < HYST_T:
            data.add(t = time() - t, **asdict(ardman.get_reading()))
            print(data.get_frame(-1))
            plt.plot(data) 

        data.dump(f'{FOLDER}/{mass}_hyst.json')
        """

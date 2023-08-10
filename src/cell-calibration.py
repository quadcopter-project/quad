# Code to calibrate a load cell.
# this is to work in conjunction with cell-calibration in ard/test

import lib.ard as ard

if __name__ == '__main__':
    arduino = ard.Arduino('/dev/ttyACM0')
    arduino.calibrate(cell_id = 0,
                      ref_mass = 100.31)

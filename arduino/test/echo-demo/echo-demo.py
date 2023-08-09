import serial
from statistics import mean, stdev
from time import time, sleep

arduino = serial.Serial('/dev/ttyACM0', baudrate=230400)

while True:
    input('begin reading: ')

    arduino.setDTR(False)
    sleep(1)
    arduino.reset_input_buffer()
    arduino.setDTR(True)

    reading = list()
    t = time()
    while time() - t < 10:
        val = float(arduino.readline()) 
        print(val)
        reading.append(val)

    print(f'{mean(reading)}, {stdev(reading)}')

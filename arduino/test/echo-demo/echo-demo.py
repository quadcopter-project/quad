import serial
from statistics import mean

arduino = serial.Serial('/dev/ttyACM0', baudrate=9600)

try:
    input('begin reading'):
    while True:
        

import os, time
import numpy as np

from datetime import datetime
from lib import ard, plotter, utils, drone, droneImage
from dataclasses import asdict
from numbers import Number

import live_bf_2

from camera import *

def init_file(path_to_txt):
    headings=["Ultrasound", "Ruler", "Pixel"]
    with open(path_to_txt,'a') as file:
        formatted_headings= "#{:<15} {:<15} {:<15}".format(*headings)
        file.write(formatted_headings+"\n")

def calibrate(live, height_queue: list, camera, path_to_txt):
    headings=["Ultrasound", "Ruler", "Pixel"]

    with open(path_to_txt,'a') as file:

        formatted_headings= "#{:<15} {:<15} {:<15}".format(*headings)
        file.write('#'+datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M")+"\n")
        file.write(formatted_headings+"\n")

        for height in height_queue:
            print(f"\nBFLive::start: Setting height to {height}cm...")
            live.set_height(height)
            print(f"BFLive::start: Height set to {height}cm.")

            drone_image=camera.take_picture(save=False,return_=True)

            image=droneImage.DroneImage(image=np.rot90(drone_image, k=3))

            print("Calculating pixel height...")
            image.get_height()
            print(f"Pixel height is {image.pixel_height}.")
            print(f"Converted height is {image.converted_height}.")
            image.imshow("contours")
            #image.display("contours")

            pixel_height=image.pixel_height

            ruler_height=input("Take your measurement...")
            while True:
                try:
                    ruler_height = float(ruler_height)
                    break 
                except ValueError:
                    ruler_height=input("Input should be a float, retry...")   

            formatted_row=f"{height:<15.3f} {float(ruler_height):<15.1f} {pixel_height:<15.3f}"
            file.write(formatted_row+"\n")

        file.write("\n\n")



if __name__ == '__main__':

    #height_queue=np.arange(37,12,-5).tolist()
    height_queue=[12,25,52,57,62]
    #init_file('measurements.txt')
    camera=Camera(serial_number='18181990',save_path='')
    live = live_bf_2.BFLive(path = 'C:/Users/zc345-elev/Documents/quad/src')

    calibrate(live=live,
               height_queue = height_queue,
               camera=camera,
               path_to_txt='measurements.txt')



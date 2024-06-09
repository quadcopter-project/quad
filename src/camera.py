from datetime import datetime
import time
import os

import numpy as np
from PIL import Image

from rotpy.system import SpinSystem
from rotpy.camera import CameraList

from lib.droneImage import *

class Camera:
    camera: None
    serial_number: str=''
    image_shape: list=()

    def __init__(self, serial_number:str, save_path,image_shape=(1200,1920)):
        self.serial_number=serial_number
        self.image_shape=image_shape
        self.save_path=save_path

        self.connect_camera()
        self.camera.init_cam()

        self.set_image_shape()
        print("Camera::__init__: init complete.")
        

    def connect_camera(self):
        # Connect camera using its serial number. initialize camera and set height and width.

        system = SpinSystem()
        cameras = CameraList.create_from_system(system, update_cams=True, update_interfaces=True)
        self.camera = cameras.create_camera_by_serial(self.serial_number)



    def set_image_shape(self):

        if self.camera.is_init():
            if len(self.image_shape)==2:
                if self.camera is not None:

                    self.camera.camera_nodes.Height.set_node_value(self.image_shape[0])
                    self.camera.camera_nodes.Width.set_node_value(self.image_shape[1])
            else:
                print("Exception: image shape should have format (height<=1200, width<=1920).")
        else:
            print("Exception: Initialize camera before setting shape.")


    def deactivate(self):
        if self.camera is not None:
            if self.camera.is_init():
                if self.camera.is_streaming():
                    self.camera.end_acquisition()
                self.camera.deinit_cam()
                self.camera.release()

        

    def save_image(self, rotpy_image,filename):
        #convert rotpy.image.Image object to .png and save.

        data = rotpy_image.deep_copy_image(rotpy_image).get_image_data()
        image_array = np.frombuffer(data, dtype=np.uint8).reshape(self.image_shape) 
        image=Image.fromarray(np.rot90(image_array, k=3))

        timestamp=datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        figpath = self.save_path+f"/{filename}{timestamp}.png"
        image.save(figpath)

        #plt.imshow(np.rot90(image_array, k=1),cmap='gray')



    def take_picture(self,filename='',save=True, return_=False,mute=False):
        self.camera.begin_acquisition()
        
        rotpy_image = self.camera.get_next_image()
        if save:
            self.save_image(rotpy_image,filename)

        if return_: 
            data = rotpy_image.deep_copy_image(rotpy_image).get_image_data()
            image_array = np.frombuffer(data, dtype=np.uint8).reshape(self.image_shape) 
        rotpy_image.release()

        self.camera.end_acquisition()

        if not mute:
            print(f"Camera::take_picture: Picture taken. Time:{datetime.fromtimestamp(time.time())}.")
        if return_:
            return image_array

    def get_height(self):
        image=self.take_picture(save=False,return_=True,mute=True)
        drone_image=DroneImage(image=np.rot90(image, k=3))
        drone_image.get_height()
        return drone_image.converted_height
            




if __name__ == '__main__':
    save_path='images'
    os.makedirs(save_path, exist_ok=True)

    camera=Camera(serial_number='18181990',save_path=save_path)
    
    
    while True:
        #take a picture every 3 seconds
        input("Camera:: Press enter to take a picture...")
        camera.take_picture()
        #time.sleep(3)


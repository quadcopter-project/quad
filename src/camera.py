from datetime import datetime
import time
import os

import numpy as np
from PIL import Image

from rotpy.system import SpinSystem
from rotpy.camera import CameraList

class Camera:
    camera: None
    serial_number: str=''
    image_shape: list=()

    def __init__(self, serial_number:str, save_path,image_shape=(1200,1920)):
        self.serial_number=serial_number
        self.image_shape=image_shape
        self.save_path=save_path

        self.connect_camera()
        self.set_image_shape()


    def connect_camera(self):
        # Connect camera using its serial number. initialize camera and set height and width.

        system = SpinSystem()
        cameras = CameraList.create_from_system(system, update_cams=True, update_interfaces=True)
        self.camera = cameras.create_camera_by_serial(self.serial_number)

    def set_image_shape(self):
        if self.camera.is_streaming() or self.camera.is_init():
            self.deactivate
        self.camera.init_cam()
        if len(self.image_shape)==2:
            if self.camera is not None:

                self.camera.camera_nodes.Height.set_node_value(self.image_shape[0])
                self.camera.camera_nodes.Width.set_node_value(self.image_shape[1])
        else:
            print("Exception: image shape should have format (height<=1200, width<=1920).")
        self.camera.deinit_cam()



    def deactivate(self):
        if self.camera is not None:
            if self.camera.is_init():
                if self.camera.is_streaming():
                    self.camera.end_acquisition()
                self.camera.deinit_cam()
                self.camera.release()

    def restart_streaming(self):

        self.deactivate()
        self.camera.init_cam()
        self.camera.begin_acquisition()


    def save_image(self, rotpy_image):
        #convert rotpy.image.Image object to .png and save.

        data = rotpy_image.deep_copy_image(rotpy_image).get_image_data()
        image_array = np.frombuffer(data, dtype=np.uint8).reshape(self.image_shape) 
        image=Image.fromarray(np.rot90(image_array, k=1))

        timestamp=datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        print(f"Picture taken: {timestamp}")
        figpath = self.save_path+f"/{timestamp}.png"
        image.save(figpath)

        #plt.imshow(np.rot90(image_array, k=1),cmap='gray')



    def take_picture(self):
        rotpy_image = self.camera.get_next_image()
        self.save_image(rotpy_image)
        rotpy_image.release()






if __name__ == '__main__':
    save_path='images'
    camera=Camera(serial_number='18181990',save_path=save_path)
    camera.restart_streaming()
    

    while True:
        #take a picture every 30 seconds
        
        camera.take_picture()
        time.sleep(30)


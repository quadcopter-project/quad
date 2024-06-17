from datetime import datetime
import time
import os

import numpy as np
from PIL import Image

from rotpy.system import SpinSystem
from rotpy.camera import CameraList

from lib.droneImage import *

## generate test image from Camera 
save_path='./temp_images/'
camera=Camera(serial_number='18181990',save_path=save_path)



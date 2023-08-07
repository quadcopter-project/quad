import time
from lib import drone

if __name__ == '__main__':
    quad = drone.Drone('../bf-conf/debug/betaflight-configurator/linux64/betaflight-configurator')
    quad.set_arming(True)
    quad.set_throttle(1010)
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        quad.set_arming(False)
    quad.set_arming(False)

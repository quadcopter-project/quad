import utils, drone, time

if __name__ == '__main__':
    ard = utils.Arduino()
    bf = drone.Drone(path = '../bf-conf/debug/betaflight-configurator/linux64/betaflight-configurator')
    bf.set_arming(True)

    throttle = 1200
    rpm = 8500
    bf.set_rpm_worker_on(True)
    bf.set_rpm(rpm)
    try:
        while True:
            mass = sum(ard.get_mass())
            bf_rpm = bf.get_rpm()
            print(f'throttle = {throttle}, rpm = {bf_rpm}, mass = {mass}')
            if mass > 200 or sum(bf_rpm) / 4 > 10000:
                break

            time.sleep(1)

    except KeyboardInterrupt:
        bf.set_arming(False)
        print(f'throttle = {throttle}')

    print(f'throttle = {throttle}')
    bf.set_arming(False)

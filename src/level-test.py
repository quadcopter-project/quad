import lib.ard, time

if __name__ == '__main__':
    ardman = lib.ard.ArdManager()
    ard = ardman.arduinos[0]
    ard.move([-400, -400, -400])
    while True:
        print(ard.get_reading())
        time.sleep(0.5)

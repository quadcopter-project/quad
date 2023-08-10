import lib.ard, time

if __name__ == '__main__':
    ardman = lib.ard.ArdManager()
    while True:
        print(ardman.get_reading())
        time.sleep(0.5)

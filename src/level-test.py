import lib.ard, time

if __name__ == '__main__':
    ardman = lib.ard.ArdManager()
    ardman.move(-2000)
    while True:
        print(ardman[0].get_reading())
        time.sleep(0.5)

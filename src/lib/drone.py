import os, time
from threading import Thread
from autobahn.twisted.websocket import WebSocketServerProtocol
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerFactory


# makes use of websocket to communicate with patched betaflight-configurator,
# its control of RPM wrapped and abstracted.
class Drone:
    NUM_OF_MOTORS:int = 4 
    MIN_THROTTLE:int = 1000
    # Drone gives about 200g lift at this throttle < 280g, its weight.
    MAX_THROTTLE:int = 1525
    throttle:list = [MIN_THROTTLE] * NUM_OF_MOTORS      # motor indices run from 0 
    armed = False
    rpm = None
    power = None
    target = [0] * NUM_OF_MOTORS # rpm target
    rpm_control_on = False # rpm_worker only responds when this is set to True.
    conn = False    # connectivity to betaflight-configurator 
    rpm_thread = None

    class ServerProtocol(WebSocketServerProtocol):
        # try not to overload __init__, in which the protocol may do weird stuff.
        connections = list()

        def onConnect(self, request):
            self.connections.append(self)
            # YES, THIS IS BETTER, BUT WE SHOULD WAIT FOR RESPONSE
            # IN onMessage(), SO THAT DATA IS PROPERLY INITIALISED, 
            # BEFORE WE DO THIS.
            # self.get_out_self().conn = True

        def onClose(self, wasClean, code, reason):
            self.connections.remove(self)
            self.get_out_self().conn = False

        def onMessage(self, payload, isBinary):
            out_self = self.get_out_self()
            out_self.conn = True
            #reply = out_self.reply
            message = payload.decode('utf8').strip().split(" ")
            header = message[0]

            """ Protocol: received from betaflight
            Header and message separated by space.
            Spaces at front and back are ignored.
            HEADER ----     MESSAGE ----
            MOTOR           rpm1,rpm2,rpm3,rpm4 
            ARMING          1(on) / 0(off)
            POWER           power1,power2,power3,power4
            """

            match header:
                case 'ARMING':
                    armed = bool(int((message[1])))
                    out_self.armed = armed

                # as of now this does not seem to work.
                case 'POWER':
                    data = message[1].split(",")
                    data = [float(entry) for entry in data]
                    out_self.power = data[:out_self.NUM_OF_MOTORS]

                case 'MOTOR':
                    data = message[1].split(",")
                    data = [int(entry) for entry in data]
                    # shorten list to only include available motors
                    out_self.rpm = data[:out_self.NUM_OF_MOTORS]

        def get_out_self(self):
            return self.factory.out_self

        # an incredibly dirty method, but it just works(TM).
        # see this post https://stackoverflow.com/a/34573420
        @classmethod
        def send(self, data):
            payload = data.encode('utf8')
            for c in set(self.connections):
                reactor.callFromThread(self.sendMessage, c, payload)

    def __init__(self, path:str = None, port: int = 3000):
        self.socket_init(port)
        self.launch_betaflight(path)

        # wait for connection to be established
        while not self.conn:
           time.sleep(1) 

        print('Drone::__init__: init complete.')

    def socket_init(self, port:int = 3000):
        self.port = port
        
        # also a bad idea to overwrite the __init__ here
        # because that __init__ does weird ass shit.
        self.factory = WebSocketServerFactory()

        # here the protocol class is passed in
        # not the instance - so can't pass in out_self at this stage.
        self.factory.protocol = self.ServerProtocol

        # but we can manually add variables...!
        self.factory.out_self = self
                
        self.socket_thread = Thread(target=self.socket_worker)
        self.socket_thread.start()

    def socket_worker(self):
        reactor.listenTCP(self.port, self.factory)

        # installSignalHandlers required for reactor to run on another thread.
        # https://stackoverflow.com/questions/12917980/non-blocking-server-in-twisted
        reactor.run(installSignalHandlers = False)

    def send(self, data):
        self.ServerProtocol.send(data)

    # quiet: redirect betaflight-configurator STDERR to /dev/null.
    # NOTE: THIS WILL BREAK ON WINDOWS.
    def launch_betaflight(self, path: str = None, quiet:bool = True):
        self.path = path
        if not path:
            return
        
        param = '&'
        if quiet:
            param = '> /dev/null 2>&1 &'

        os.system(path + " " + param)

    def close(self):
        self.set_rpm_worker_on(False)
        self.set_arming(False)

    def set_arming(self, armed:bool = False, block = True):
        if not armed:
            self.set_rpm_worker_on(False)

        message =  'ARMING ' + ('1' if armed else '0')
        self.send(message)
        
        # block: Wait until betaflight arming status is correctly updated.
        while block and (self.armed is not armed):
            time.sleep(0.5)

    def set_throttle_for_motor(self, ind:int, throttle: int):
        if (ind >= self.NUM_OF_MOTORS):
            print('Drone::set_throttle_for_motor: max index exceeded')
            return
        
        if not self.armed:
            print('Drone::set_throttle_for_motor: unable to set throttle when unarmed')
            return
            
        # throttle must be between max and min
        throttle = max(throttle, self.MIN_THROTTLE)
        throttle = min(throttle, self.MAX_THROTTLE)

        self.throttle[ind] = throttle
        throttle_string = " ".join([str(val) for val in self.throttle])
        self.send(f'SET {throttle_string}')

    # throttle: int will set all motors to the same throttle
    def set_throttle(self, throttle:int|list):
        # int, then assume same throttle for all
        if type(throttle) is int:
            throttle = [throttle] * self.NUM_OF_MOTORS

        for i in range(len(throttle)):
            self.set_throttle_for_motor(i, throttle[i])

    # only function that accesses self.target directly 
    def set_rpm_for_motor(self, ind:int, target:int):
        if (ind > self.NUM_OF_MOTORS):
            print('Drone::set_rpm_for_motor: maximum motor index exceeded.')
            return

        self.target[ind] = target

    # target: int will set all motors to the same rpm.
    # block = True: The function will block until all RPMs are different from their target within pm RPM_TOLERANCE.
    def set_rpm(self, target:int|list, block:bool = False):
        RPM_TOLERANCE:float = 150
        if type(target) is int:
            target = [target] * self.NUM_OF_MOTORS

        for i in range(len(target)):
            self.set_rpm_for_motor(i, target[i])

        if block:
            rpm = self.get_rpm()
            abs_diff = [abs(target[i] - rpm[i]) for i in range(self.NUM_OF_MOTORS)]
            while any(diff > RPM_TOLERANCE for diff in abs_diff):
                time.sleep(0.5)
                rpm = self.get_rpm()
                abs_diff = [abs(target[i] - rpm[i]) for i in range(self.NUM_OF_MOTORS)]

    # start / stop rpm_worker in its own thread.
    # must be called explicitly for rpm control to take over.
    def set_rpm_worker_on(self, on = False):
        if (not on):
            # signal the worker to quit
            self.rpm_control_on = False
            # reset rpm. A design choice: If rpm worker is off, 
            # then the rpm should become unmaintained and keep spinning.
            # However when one switch it on again next time, it should
            # have a reproducible behaviour (same as fresh start.)
            self.set_rpm(0)
            if (self.rpm_thread):
                # and wait for it to actually quit
                self.rpm_thread.join()

        elif on:
            # start thread only if it wasn't already present
            if (not self.rpm_thread) or (not self.rpm_thread.is_alive()):
                # reset rpm targets, ignoring any previous commands
                self.set_rpm(0)
                self.rpm_control_on = True
                self.rpm_thread = Thread(target = self.rpm_worker)
                self.rpm_thread.start()

    def rpm_worker(self):
        print('Drone::rpm_worker: started.')
        while True:
            if (not self.rpm_control_on) or (not self.armed):
                print('Drone::rpm_worker: exit signal received.')
                break

            for i in range(self.NUM_OF_MOTORS):
                rpm = self.rpm[i]
                throttle = self.throttle[i]
                target_rpm = self.target[i]
                target_throttle = self.MIN_THROTTLE

                # TODO: FOR NOW, ALLOW FOR AN ERROR OF +- 75.
                if not target_rpm: # motor simply not on
                    target_throttle = self.MIN_THROTTLE
                # Quick adjustments
                else:
                    target_throttle = throttle + (target_rpm - rpm) // 100
                # the target should not go below MIN_THROTTLE, or above MAX_THROTTLE.
                # this is taken care of in the set_throttle_for_motor function.
                self.set_throttle_for_motor(i, target_throttle)

            # allows for up to 2 modulations per sec.
            # the polling rate allows for higher frequency, but DShot actually doesn't update that frequently
            time.sleep(0.5)

    def get_avg_rpm(self) -> float:
        return sum(self.rpm[:self.NUM_OF_MOTORS]) / self.NUM_OF_MOTORS

    def get_rpm(self) -> list:
        return self.rpm 


# PRIVATE testing methods; will break if called outside this scope (bf object not initialsed).
def test_switch():
    print('TESTING SWITCH...')
    bf.set_arming(True)
    time.sleep(5)
    bf.set_arming(False)
        
def test_throttle():
    print('TESTING THROTTLE CONTROL...')
    print('test set_throttle(list)')
    bf.set_throttle([1020, 1020, 1020, 1020])
    time.sleep(10)

def test_rpm():
    print('TESTING RPM CONTROL...')
    # init
    bf.set_rpm_worker_on(True)

    print('test set_rpm(target:int)')
    bf.set_rpm(2000)
    time.sleep(10)
    bf.set_rpm(0)

    print('test set_rpm_for_motor')
    bf.set_rpm_for_motor(0, 1800)
    bf.set_rpm_for_motor(1, 1800)
    bf.set_rpm_for_motor(2, 1800)
    bf.set_rpm_for_motor(3, 1800)
    time.sleep(10)
    bf.set_rpm_worker_on(False)

    print('rpm_worker off: motors should keep spinning at same throttle.')
    time.sleep(10)

    print('test set_rpm(target:list). Motor may jolt initially.')
    bf.set_rpm_worker_on(True)
    bf.set_rpm([1700, 1700, 1700, 1700])
    time.sleep(10)

    bf.set_rpm_worker_on(False)

if __name__ == '__main__':
    print('LAUNCHED AS MAIN - COMMENCING TESTING...')
    input('Confirm start: ')
    bf = Drone(path = '../../bf-conf/debug/betaflight-configurator/linux64/betaflight-configurator')
    test_switch()
    bf.set_arming(True)
    test_throttle()
    test_rpm()
    bf.set_arming(False)
    
    print('Testing completed.')

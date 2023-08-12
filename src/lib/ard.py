"""ard.py
Experimental new classes for arduino interfacing.
null value return on disconnect state is scrapped. It now assumes that device is connected.
"""

import serial, json, os, time
import serial.tools.list_ports
import numpy as np

from dataclasses import dataclass, field, asdict
from threading import Thread
from numpy import array
from numpy.linalg import norm


# contains a single frame of Arduino reading
# could either be a return value of Arduino or ArdManager's get_reading().
@dataclass
class ArdReading:
    accel: list = field(default_factory = list) # list of accelerometers; each reading is a vector
    dist: list = field(default_factory = list)
    mass: list = field(default_factory = list)
    motor: list = field(default_factory = list)
    # a pseudo-list. Arduino will only ever return list of one value indictaing its state.
    # However, this helps keep the code free of special cases
    operating: list = field(default_factory = list)

    def load(self, output_dict: dict):
        for key, value in output_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)


# wrapper for arduino class
# useful for auto-scanning and connecting to multiple arduinos simultaneously.
# individual arduinos with id {n} can be accesses by calling ArdManager[n].
class ArdManager:
    arduinos: dict = dict()  # list of Arduino objects. dev_id -> arduino
    mapping = None

    @dataclass
    class ArdMapping:
        accel: list = field(default_factory = list)
        dist: list = field(default_factory = list)
        mass: list = field(default_factory = list)   # motor id -> (dev_id, #motor_output)
        motor: list = field(default_factory = list)
        operating: list = field(default_factory = list)

        def dump(self, name):
            if os.path.isfile(name):
                raise IOError(f'(E) ArdMapping::dump: {name} already exists.')

            with open(name, 'w') as file:
                file.write(json.dumps(self.__dict__, indent = 4))

        def load(self, name):
            if not os.path.isfile(name):
                raise IOError(f'(E) ArdMapping::load: {name} does not exist.')
            with open(name) as file:
                mapping_json = file.read()
                mapping_dict = json.loads(mapping_json)

                for comp, comp_map in mapping_dict.items():
                    if hasattr(self, comp):
                        setattr(self, comp, comp_map)

    def __init__(self, baud:int = 230400, config_name: str = None):
        self.ports = list(serial.tools.list_ports.grep('0043'))  # filter for arduino devices by their PID
        print(f'ArdManager::__init__: found {len(self.ports)} Arduinos.')
        for port in self.ports:
            print(f'ArdManager::__init__: initialising {port.description} on {port.device}.')
            ard = Arduino(port.device, baud)
            self.arduinos[ard.dev_id] = ard 

        self.arduinos = dict(sorted(self.arduinos.items()))

        # this is for the readline_workers to be properly initialised.
        time.sleep(2)

        if config_name:
            self.load(config_name)
        else:
            self.gen_mapping()

        print('ArdManager::__init__: init complete.')

    def __getitem__(self, key):
        return self.arduinos[key]

    # infer mapping from arduino readings, and save them to self.mapping
    # the mapped component id's are in order of ascending dev_id and comp_id
    def gen_mapping(self):
        mapping = self.ArdMapping()

        for dev_id, arduino in self.arduinos.items():
            reading = arduino.get_reading()
            
            for comp, values in asdict(reading).items():
                comp_map = getattr(mapping, comp)
                # would have used tuples but json parses them to lists, so use lists for consistency.
                comp_map.extend([ [dev_id, comp_id] for comp_id in range(len(values)) ])

        self.mapping = mapping

    # interactively adjust component mapping: supports motors and cells.
    # the final mapping is written back to self.mapping. 
    def customise_mapping(self):
        old_mapping = self.mapping
        new_mapping = self.ArdMapping()

        if not old_mappping:
            raise Exception('(E) ArdManager::customise_mapping: No original mapping to work from.')

        # initialise new_mapping with None entries
        for comp, comp_map in asdict(old_mapping):
            setattr(new_mapping, comp, [None] * len(comp_map))

        print('ArdManager::customise_mapping: Remapping motors.')
        max_id = len(old_mapping.motor)
        for i in range(max_id):
            dev_id, motor_id = old_mapping.motor[i] 
            new_id = ''
            while True:
                input(f'Motor {i} will now move 90 degrees. Confirm: ')
                self.arduinos[dev_id].move(motor_id, 90)
                new_id = input('Assign new id to this motor: ')
                if not new_id.isnumeric():
                    print('Invalid input.')
                else:
                    new_id = int(new_id)
                    if new_id < 0 or new_id > max_id:
                        print('Invalid number.')
                    elif new_mapping.motor[new_id] is not None:
                        print(f'New id already used.')
                    else:
                        break
            new_mapping.motor[new_id] = old_mapping.motor[i]
        
        print('ArdManager::customise_mapping: Remapping load cells.')
        max_id = len(old_mapping.mass)
        for i in range(max_id):
            print('Push / pull on the load cell to be assigned new id {i}.')
            old_id = None
            while True:
                mass = self.get_reading().mass
                for i in range(len(mass)):
                    if abs(mass[i]) > 50:
                        old_id = i
                        break
                if old_id is not None:
                    break
                time.sleep(0.5)
            new_mapping.mass[i] = old_mapping.mass[old_id]

        # overriding sub-entries, as new_mapping.accel and new_mapping.dist are still [None].
        old_mapping.motor = new_mapping.motor
        old_mapping.mass = new_mapping.mass

    
    # GET functions (public)

    # obtain combined reading, in the order of mapped components.
    # return -> ArdReading object, containing all available readings.
    def get_reading(self) -> ArdReading:
        reading = ArdReading()
        dev_reading = {dev_id: arduino.get_reading() for dev_id, arduino in self.arduinos.items()}

        for comp, comp_map in asdict(self.mapping).items():
            comp_reading = getattr(reading, comp) 
            # put readings in according to id order
            for dev_id, comp_id in comp_map:
                dev_comp_reading = getattr(dev_reading[dev_id], comp)
                comp_reading.append(dev_comp_reading[comp_id])

        return reading

    def get_mass(self) -> list:
        return self.get_reading().mass

    def get_accel(self, accel_id: int = 0) -> list:
        return self.get_reading().accel[accel_id]


    # DEVICE CONTROL functions (public)

    # instruct motors to move by a number of STEPS.
    # target: list must specify individual motors;
    # target: int moves all motors by same steps.
    # block = True will block the function until motors finish.
    def move(self, target: int|list, block:bool = False):
        motor_num = len(self.mapping.motor)

        if type(target) is int:
            target = [target] * motor_num

        if len(target) != motor_num:
            raise Exception('(E) ArdManager::move: target list does not match number of motors.')

        target_by_dev = dict()
        for i in range(motor_num):
            dev_id, comp_id = self.mapping.motor[i]
            if dev_id not in target_by_dev.keys():
                target_by_dev[dev_id] = dict()
            target_by_motor = target_by_dev[dev_id]
            target_by_motor[comp_id] = target[i]

        for dev_id, target_by_motor in target_by_dev.items():
            target_by_motor = dict(sorted(target_by_motor.items()))     # NOTE: THIS WILL DEREFERENCE target_by_motor.
            # do not block here, so we can start all motors now and block only when they are running.
            self.arduinos[dev_id].move(target_by_motor.values(), block = False)

        if block:
            time.sleep(1)
            while True:
                reading = self.get_reading()
                if True not in reading.motor:
                    break
                time.sleep(0.5)

    # wrapper for moving individual motor. 
    # target: movement in STEPS.
    def move_motor(self, motor_id: int, target: float):
        motor_num = len(self.mapping.motor)
        target = [0 if i != motor_id else target for i in range(motor_num)]
        self.move(target)

    # force all motors to stop
    def stop(self):
        for arduino in self.adruinos:
            arduino.stop()

    # dump / save current self.mapping as a json file.
    # name: position to store the file (relpath / abspath)
    def dump(self, name: str):
        if self.mapping is None:
            raise Exception('(E) ArdManager::dump: no mapping defined.')
        self.mapping.dump(name) 

    # load a self.mapping json file from disk.
    # name: location of file
    def load(self, name: str):
        if self.mapping:
            raise Exception('(E) ArdManager::load: mapping exists; Refusing to overwrite.')
        self.mapping = ArdMapping()
        self.mapping.load(name)


# interface with individual arduinos.
# issued commands will be ignored if the arduino does not have that capability.
class Arduino:
    conn: bool = False

    baud: int = None
    port: str = None
    dev_id: int = None
    dev: serial.Serial = None

    line: str = ""

    def __init__(self, port:str, baud:int = 230400):
        self.port = port
        self.baud = baud
        self.open(port, baud = baud) 
        self.reset()

        self.get_dev_info()
        self.line = self.readline() # populate a first line

        self.thread = Thread(target=self.readline_worker)
        self.thread.start()

        print(f'Arduino::__init__: initialised arduino #{self.dev_id} on {self.port}.')

    # BASIC I/O functions (private)
    def open(self, port:str, baud = 230400):
        self.dev = serial.Serial(port, baudrate = baud, timeout = None)
        self.port = port
        self.baud = baud
        self.conn = True

    def close(self):
        self.dev.close()
        self.conn = False

    def reset(self):
        self.dev.setDTR(False)
        time.sleep(1)
        self.dev.reset_input_buffer()
        self.dev.setDTR(True)
        # required for device to finish reset.
        # without this the first self.write will likely not reach the arduino.
        time.sleep(2)

    # write a line, {message} to Arduino.
    def write(self, message: str):
        self.dev.write((message + '\n').encode())

    def readline(self) -> str:
        line = self.dev.readline().decode('ascii').strip()
        return line

    # fetch most recent line that arduino prints in a background thread.
    # stores line in self.line but doesn't parse it, to save overhead.
    # NOTE: as of now it is debatable whether this is faster.
    def readline_worker(self):
        while True:
            if self.dev is None or not self.dev.is_open:
                self.conn = False
                raise Exception('(E) Arduino::readline_worker: Arduino on {self.port} disconnected.')

            self.line = self.readline()


    # GET functions (public)

    # query arduino information.
    # waits for arduino to report its dev_id, and optionally
    # calibration factors for any load cells it may have.
    # conflicts with readline_worker and can only be called in __init__.
    def get_dev_info(self):
        self.write('IDEN')
        # Getting dev_id means terminating the IDEN call.
        while self.dev_id is None:
            line = self.readline()
            parsed = line.strip().split()

            cmd = parsed[0]
            param = parsed[1:]
            match cmd:
                case 'CALIB':
                    self.calib_factor = [float(val) for val in param] 
                case 'IDEN':
                    self.dev_id = int(param[0]) 

    # return -> operating: bool
    # True: either taring load cells or motors are moving.
    def is_operating(self) -> bool:
        return True in self.get_reading().operating

    # parse the most recent arduino telemetry line then return as ArdReading object.
    # return -> reading: ArdReading
    def get_reading(self) -> ArdReading:
        parsed = self.line.strip().split(' ', maxsplit = 1)

        cmd = parsed[0] 
        if cmd != 'DAT':
            print(f'(E) Arduino::get_reading: line is of type {cmd}, cannot parse to output data.')
            print(self.line)
            return None

        output_json = parsed[1]
        output_dict = json.loads(output_json)
        reading = ArdReading()
        reading.load(output_dict)
        return reading


    # DEVICE CONTROL functions (public)

    # move by number of STEPS
    # target: list specifies all motors;
    # target: int moves all motors for the same steps. 
    def move(self, target: list, block: bool = False):
        self.write('MOVE ' + " ".join([str(steps) for steps in target]))
        
        if block:
            time.sleep(1)
            while self.is_operating():
                time.sleep(0.5)

    # instructs all motors to stop.
    def stop(self):
        self.write('STOP')
        while self.is_operating():
            time.sleep(0.2)

    def level(self):
        self.write('LEVEL')
        time.sleep(0.1)
        while self.is_operating():
            time.sleep(0.05)
            print(self.get_reading())

    def tare(self, block = False):
        self.write('TARE')
        if block:
            time.sleep(0.5)
            while self.is_operating():
                time.sleep(0.2)

    # interactively calibrate a specified load cell.
    def calibrate(self, cell_id: int, ref_mass: float):
        MASS_TOLERANCE: float = 0.01
        print(f'Arduino::calibrate: calibrating cell {cell_id} on device {self.dev_id}. ref_mass = {ref_mass}g.')
        input('Confirm balance taring: ')
        self.tare()
        input('Put standard mass on: ')
        time.sleep(2)
        
        t = time.time()
        mass = list()

        # get mass reading for 20s
        while (time.time() - t < 20):
            mass_reading = self.get_reading().mass[cell_id]
            mass.append(mass_reading)
            time.sleep(0.2)
            print(f'{mass_reading}g')
            
        mean_mass = sum(mass) / len(mass)
        print(f'average {mean_mass}')
        new_factor = self.calib_factor[cell_id] * (mean_mass / ref_mass)

        print(f'Suggested new factor: {new_factor}. Update that in Arduino source.')


if __name__ == "__main__":
    print('You are executing a library as main.')
    print('Executing test: scan arduinos and print their telemetry.')
    ardman = ArdManager()
    while True:
        print(ardman.get_reading())
        time.sleep(0.5)


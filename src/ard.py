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


@dataclass
class ArdReading:
    accel: list = field(default_factory = list) # list of accelerometers; each reading is a vector
    dist: list = field(default_factory = list)
    mass: list = field(default_factory = list)
    motor: list = field(default_factory = list)

    def load(self, output_dict: dict):
        for key, value in output_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)


class ArdManager:
    arduinos: dict = dict()  # list of Arduino objects. dev_id -> arduino
    mapping = None

    # TODO: deprecate, then remove timeout.
    def __init__(self, baud:int = 230400, timeout:float = None, config_name: str = None):
        self.ports = list(serial.tools.list_ports.grep('0043'))  # filter for arduino devices by their PID
        print(f'ArdManager::__init__: found {len(self.ports)} Arduinos.')
        for port in self.ports:
            print(f'ArdManager::__init__: initialising {port.description} on {port.device}.')
            ard = Arduino(port.device, baud, timeout)
            self.arduinos[ard.dev_id] = ard 

        self.arduinos = dict(sorted(self.arduinos.items()))

        # this is for the workers to be properly initialised.
        time.sleep(2)

        if config_name:
            self.load(config_name)
        else:
            self.gen_mapping()

        print('ArdManager::__init__: init complete.')

    # infer mapping from arduino readings: number in order of ascending dev_id and order of sensors in readings
    def gen_mapping(self):
        mapping = self.ArdMapping()

        for dev_id, arduino in self.arduinos.items():
            reading = arduino.get_reading()
            
            for comp, values in asdict(reading).items():
                comp_map = getattr(mapping, comp)
                # would have used tuples but json parses them to lists, so use lists for consistency.
                comp_map.extend([ [dev_id, comp_id] for comp_id in range(len(values)) ])

        self.mapping = mapping

    # adjust mapping of load cells & motors
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
                mass = self.get_reading().mass   #TODO: NOT IMPLEMENTED YET
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

    # angle: list of angles to move for each motor.
    def move(self, target: list, block:bool = True):
        motor_num = len(self.mapping.motor)
        if len(target) != motor_num:
            raise Exception('(E) ArdManager::move: target list does not match number of motors.')

        for i in range(motor_num):
            dev_id, comp_id = self.mapping.motor[i]
            self.arduinos[dev_id].move(comp_id, target[i])

        if block:
            while True:
                reading = self.get_reading()
                if True not in reading.motor:
                    break
                time.sleep(0.5)

    # TODO: since non-block is not safe, consider just removing it?
    def move_motor(motor_id: int, target: float, block = True):
        # TODO: define get_motor_num function
        motor_num = len(self.mapping.motor)
        target = [0 if i != motor_id else target for i in range(motor_num)]
        self.move(target, block)

    def dump(self, name: str):
        if self.mapping is None:
            raise Exception('(E) ArdManager::dump: no mapping defined.')
        self.mapping.dump(name) 

    def load(self, name: str):
        if self.mapping:
            raise Exception('(E) ArdManager::load: mapping exists; Refusing to overwrite.')
        self.mapping = ArdMapping()
        self.mapping.load(name)

    @dataclass
    class ArdMapping:
        # where no mapping is established, None is stored.
        accel: list = field(default_factory = list)
        dist: list = field(default_factory = list)
        mass: list = field(default_factory = list)   # motor id -> (dev_id, #motor_output)
        motor: list = field(default_factory = list)

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


class Arduino:
    conn: bool = False
    moving: bool = False

    baud: int = None
    port: str = None
    dev_id: int = None
    dev: serial.Serial = None

    line: str = ""

    ANGLE_PER_STEP: float = 1.8

    # NOTE: change of timeout is allowed, but unexpected behaviour might result, eg in move.
    def __init__(self, port:str, baud = 230400, timeout = None):
        self.open(port, baud = baud, timeout = timeout) 
        self.reset()
        self.get_dev_info()
        self.thread = Thread(target=self.worker)
        self.thread.start()
        print(f'Arduino::__init__: initialised arduino ID: {self.dev_id}.')

    def open(self, port:str, baud = 230400, timeout = None):
        self.dev = serial.Serial(port, baudrate = baud, timeout=timeout)
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

    def write(self, message: str):
        self.dev.write(message)

    def move(self, target: float):  # make new variable to make sure this completes before new command is issued
        steps = int(target / self.ANGLE_PER_STEP)
        self.write(f'MOVE {motor_id} {steps}')

    def get_dev_info(self):
        self.write(b'INFO')
        while not self.dev_id:
            line = self.readline()
            parsed = line.strip().split()

            cmd = parsed[0]
            param = parsed[1:]
            match cmd:
                case 'IDEN':
                    self.dev_id = int(param[0]) 
            
        if not self.dev_id:
            raise IOError('(E) Arduino::get_dev_info: unable to fetch Arduino information in 5 lines.')

    def worker(self):
        while True:
            if self.dev is None or not self.dev.is_open:
                self.conn = False
                raise Exception('(E) Arduino::worker: Arduino on {self.port} disconnected.')

            self.line = self.readline()

    def readline(self) -> str:  # TODO: Transform this into a blocking call by removing timeout
        line = self.dev.readline().decode('ascii').strip()
        return line

    # only parse self.line when requested - this saves loads of overhead
    def get_reading(self) -> ArdReading:
        parsed = self.line.strip().split(' ', maxsplit = 1)

        cmd = parsed[0] 
        if cmd != 'DAT':
            print(f'(E) Arduino::get_reading: line is of type {cmd}, cannot parse to output data.')
            return None

        output_json = parsed[1]
        output_dict = json.loads(output_json)
        readings = ArdReading()
        readings.load(output_dict)
        return readings
        
    # TODO: Rewrite this with new apis
    def calibrate(self, ind: int, ref_mass: float) -> float:
        pass

if __name__ == "__main__":
    ardman = ArdManager()
    while True:
        print(ardman.get_reading())
        time.sleep(1)


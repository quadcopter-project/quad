# Arduino 0

## Description
Arduino 0 is the "main control" in the setup. It will be connected to all the motors, an accelerometer and a an ultrasound distance sensor.

It will be capable of the following: 
- Respond to query for DEV\_ID
- Take instructions to move a motor by motor\_id
- Take instruction to initiate auto-calibration
- Take instruction to alter distance
- Return telemetry of distance sensor, accelerometer and motor state.

## Layout
| Arduino | MMA |
|---------|-----|
| 5V      | Vin |
| GND     | GND |
| A4      | SDA |
| A5      | SCL |

| Arduino | DM542T-* |
|---------|----------|
| GND     | DIR-     |
| GND     | PUL-     |

| Arduino | DM542T-1 |
|---------|----------|
| 2       | PUL+     |
| 3       | DIR+     |

| Arduino | DM542T-2 |
|---------|----------|
| 4       | PUL+     |
| 5       | DIR+     |

| Arduino | DM542T-3 |
|---------|----------|
| 6       | PUL+     |
| 7       | DIR+     |

| Arduino | HC-SR04 |
|---------|---------|
| 8       | TRIG    |
| 9       | ECHO    |

| DM542T-* | NEMA17-* |
|----------|----------|
| A+       | Red      |
| A-       | Blue     |
| B+       | Black    |
| B-       | Green    |

| DM542T-* | EP-613 (30V) |
|----------|--------------|
| +Vdc     | +            |
| GND      | -            |

| *   | EP-613 (5V) |
|-----|-------------|
| VCC | +           |
| GND | -           |

## Behaviour
Blocking functions, such as `setHeight`, will ignore server command when working. There is no guarantee these will report back during adjustment, but at the start and end of these functions they will report that motors are on / off with the `isOperating` flag. This will help with the blocking methods on Python's end.

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
Arduino     MMA8451
5V          Vin
GND         GND
A4          SNA
A5          SCL 

Arduino     DM542T-*
GND         DIR-
GND         PUL-

Arduino     DM542T-1
2           DIR+
3           PUL+

Arduino     DM542T-2
4           DIR+
5           PUL+

Arduino     DM542T-3
6           DIR+
7           PUL+

Arduino     HC-SR04 
8           TRIG
9           ECHO 

DM542T-*    NEMA17-*
A+          Red
A-          Blue
B+          Green
B-          Black

DM542T-*    EP-613 (30V)
+Vdc        +
GND         -

\*          EP-613 (5V)
VCC         +
GND         -

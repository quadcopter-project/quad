/*
===Stepper motor demo===

---DESCRIPTION---
Controls a stepper motor from a DM542T digital stepper driver.

The DM542T has been chosen in favour of L298N, which exhibits several problems:
- Overheats quickly
- Very current hungry, consuming 2A at 4V and still current limited and unable to drive the motor effectively.
- Dramatically jolts the motor on Arduino reset.
- Broken easily after a few Arduino resets.

The DM542T on the other hand can be used with a power supply at 30V ~0.11A, and operation range is all the way from 18V to 50V. Note that, if the motor moves jerkily and vibrates a lot, it is likely current-starved. Since DM542T is able to control current itself, one can just turn the current limit nob all the way to the maximum.

In order to test which two wires on the motor belong to the same coil, one can use the continuity test mode on a multimeter. Ones that register a sound belong to the same pair. The convention tends to be (red, blue) and (green, black).

---COMPONENTS---
- Stepperonline DM542T Digital Stepper Driver V4.0
- RS PRO Hybrid, Permanent Magnet Stepper Motor, 0.44Nm Torque, 2.8 V, 1.8°, 42.3 x 42.3mm Frame, 5mm Shaft (NEMA-17)
- PS3025 / EP-613 0 - 30V 2.5A DC Power Supply
- Arduino UNO

---LAYOUT---
Arduino <-> DMT542T
9           PUL+
GND         PUL-
8           DIR+
GND         DIR-

DMT542T <-> NEMA-17 (two sets of coils)
A+          RED
A-          BLUE
B+          GREEN
B-          BLACK

DMT542T <-> EP-613
+Vdc        +
GND         -

---REFERENCE---
DM542T manual: https://www.omc-stepperonline.com/download/DM542T_V4.0.pdf
NEMA-DM542T: https://vslot-poland.com/how-to-connet-arduino-to-nema
Motor: https://uk.rs-online.com/web/p/stepper-motors/5350489
DM542T V4.0: https://www.omc-stepperonline.com/digital-stepper-driver-1-0-4-2a-20-50vdc-for-nema-17-23-24-stepper-motor-dm542t
AccelStepper library: https://www.airspayce.com/mikem/arduino/AccelStepper/classAccelStepper.html
*/
#include <AccelStepper.h>

AccelStepper stepper(AccelStepper::DRIVER, 9, 8);

void setup()
{
    // for stepper.run(), this function is required instead of setSpeed().
	stepper.setMaxSpeed(60);
    stepper.setAcceleration(200);
    stepper.setCurrentPosition(0);
    stepper.move(-10000);
	Serial.begin(9600);
}

void loop() 
{
   stepper.run();
}

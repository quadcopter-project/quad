# arduino/

This folder contains C++ code for the Arduinos. The "production" code are put in
the `ardn` folders, where n is the DEV\_ID of the Arduino. There's nothing
special about any of these Arduinos but we label the hardware for consistency.

The other folders mainly contain test or demo code. Their names should be
self-explanatory.

It should be noted that in the new set up, **only `ard0` is still being used**.
One should consider code for the other Arduinos obsolete.


## Libraries

The following libraries have been used.

- HX711 load cell amplifier: [HX711 Arduino
  Library](https://www.arduino.cc/reference/en/libraries/hx711-arduino-library/)
- MMA8451 accelerometer: [Adafruit MMA8451
  Library](https://www.arduino.cc/reference/en/libraries/adafruit-mma8451-library/)
- Stepper motors:
  [AccelStepper](https://www.arduino.cc/reference/en/libraries/accelstepper/)
- HC-SR04 sonar distance sensor: Handwritten, which offers better precision (but
  perhaps not much more accuracy!) than
  [NewPing](https://www.arduino.cc/reference/en/libraries/newping/)


## I don't like the parameters!

The code was written with parameter tuning in mind. All the tunable parameters
appear as consts in upper case at the top of the files.


## Known issues

Sometimes the Arduino (in particular, Arduino #0) becomes unresponsive and stops
reporting data/status. To resolve it, the Arduino might have to be reset. It has
been observed that with fewer samples in accelerometer reading the problem is
alleviated: The associated parameters are `ACCEL_MEAN_REPEATS` and
`ACCEL_DELAY`. However decreasing those will come at the cost of longer,
potentially unacceptable levelling times.

As far as I can tell the main program is free of global variable declarations
outside initialization and excessive memory use, and the suspicion has been that
there is a problem with memory management (e.g. heap fragmentation) in the
libraries.

The Arduino code would also benefit significantly from the creation of
_libraries_ that collect the overlapping code between Arduinos. I had
difficulties doing this because of the way `arduino-cli` handles libraries.

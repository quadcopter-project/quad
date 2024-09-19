# Arduino 4

## Description
Arduino 4 connects to light gates measuring rpm of propeller number 1 and 2. Only 2 light gates are supported for 1 Arduino due to the limitation of interrupt pins. 

Operation loop:
- Respond to query for DEV\_ID
- Every time a rising edge is detected, trigger interrupt and put time interval between last 2 rising edge into buffer.
- Calculate rpm through time interval buffer and return formatted value through serial if possible

## Layout
| Arduino | Light gates |
| -------------- | --------------- |
| 2 | propeller 1 |
| 3 | propeller 2 |



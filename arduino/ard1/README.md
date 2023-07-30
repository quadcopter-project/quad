# Arduino 1

## Description
Arduino 1 is on its own and connects to three load cells (TAL221, 500g), via three HX711 amplifiers.

It will be capable of the following:
- Repond to query for DEV\_ID
- Return telemetry of the load cells. 

## Layout
| TAL221 | HX711 |
|--------|-------|
| Red    | E+    |
| Black  | E-    |
| White  | A-    |
| Green  | A+    |

| Arduino | HX711-1 |
|---------|---------|
| 3       | DT      |
| 2       | SCK     |

The next two HX711's have `DT`, `SCK` at 5, 4 and 7, 6 respectively.

| EP-613 (5V) | HX711-* |
|-------------|---------|
| -           | GND     |
| +           | Vcc     |


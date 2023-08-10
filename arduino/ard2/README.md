# Arduino 2

## Description
Arduino 2 is connects to 6 load cells (TAL221, 500g), via 6 HX711 amplifiers.

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

The other HX711's have `DT`, `SCK` at 5, 4 and 7, 6, etc. Three load cells on the same mount are to have their pins next to each other.

| EP-613 (5V) | HX711-* |
|-------------|---------|
| -           | GND     |
| +           | Vcc     |


# Arduino 3

## Description
Arduino 3 is on its own and connects to three load cells (TAL221, 100g), via three HX711 amplifiers. The only difference between this and Arduino 1 code is that this arduino uses 100g TAL221 and is meant to work with the new "balance" design.

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


/*
 Code by Nathan Seidle of Sparkfun Electronics, modified for the quadcopter project.

 Taken from HX711-Load-Cell-Amplifier on Github.

 Zeroes balance upon power on and simply outputs the mass reading on the load cell.
 
*/

#include "HX711.h"

#define CELLS 3
#define DEVICE_ID 0

const int LOADCELL_DOUT_PIN[CELLS] = {3, 5, 7};
const int LOADCELL_SCK_PIN[CELLS] = {2, 4, 6};
const float calibration_factor[CELLS] = {16665.8, 16886.6, 16678};

HX711 scales[CELLS];


void setup() {
  Serial.begin(230400);
  Serial.print("IDEN ");
  Serial.println(DEVICE_ID);

  for (int i = 0; i < CELLS; i++) {
    HX711& scale = scales[i];
    scale.begin(LOADCELL_DOUT_PIN[i], LOADCELL_SCK_PIN[i]);
    scale.set_scale();
    scale.tare();
  }
}

void loop() {
  for (int i = 0; i < CELLS; i++) {
    HX711& scale = scales[i];
    float calib = calibration_factor[i];
    scale.set_scale(calib); //Adjust to this calibration factor
    Serial.print(scale.get_units(), 5);
    Serial.print(" "); 
  }

  delay(500);
/*
  Serial.print(" calibration_factor: ");
  Serial.print(calibration_factor);
*/
  Serial.println();

/*
  if(Serial.available())
  {
    char temp = Serial.read();
    if(temp == '+' || temp == 'a')
      calibration_factor += 10;
    else if(temp == '-' || temp == 'z')
      calibration_factor -= 10;
  }
*/
}

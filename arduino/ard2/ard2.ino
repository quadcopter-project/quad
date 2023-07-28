/*
Purely procedural, and global variables,
that's the way it shall be...
*/

#include <NewPing.h>
#include <AccelStepper.h>

const int DEVICE_ID = 2;

// motor configs
const int NUM_MOTOR = 1;
const double DEG_PER_STEP = 1.8;
const int STEP_PER_REV = int(360 / DEG_PER_STEP);
const int STEPPER_SPEED = 1000;
const int IN1[NUM_MOTOR] = {7};
const int IN2[NUM_MOTOR] = {6};
const int IN3[NUM_MOTOR] = {5};
const int IN4[NUM_MOTOR] = {4};
AccelStepper motor[NUM_MOTOR];

char str[20];
char substr[20];
int len = 0;
int sublen = 0;
int pos = 0;

void readline() {
    len = sublen = pos = 0;
    while (Serial.available()) {
        char ch = Serial.read();
        if (ch == '\n') {
            str[len] = '\0';
            break;
        }
        str[len++] = ch;
    }
}

void next_substr() {
    sublen = 0;
    while (pos < len) {
        if (str[pos] == ' ') {
            substr[sublen] = '\0';
            pos++;
            break;
        }
        substr[sublen++] = str[pos++];
    }
}

int substr_to_int() {
    int val = 0;
    for (int i = 0; i < sublen; i++) {
        val = val * 10 + (substr[i] - '0');
    }
    return val;
}

void setup() {
    for (int i = 0; i < NUM_MOTOR; i++) {
        motor[i] = AccelStepper(AccelStepper::FULL4WIRE, IN1[i], IN2[i], IN3[i], IN4[i]);
        motor[i].setSpeed(STEPPER_SPEED);
        motor[i].setCurrentPosition(0);
        // debug
        motor[i].move(1000);
    }
    Serial.begin(230400);
}

void loop() {
    for (int i = 0; i < NUM_MOTOR; i++) {
        motor[i].run();
    }
}

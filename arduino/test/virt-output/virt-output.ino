/*
Purely procedural, and global variables,
that's the way it shall be...
*/

#include <NewPing.h>
#include <AccelStepper.h>

const int DEVICE_ID = 1;
const int NUM_MOTOR = 0;

const int TRIGGER_PIN = 11;
const int ECHO_PIN = 12;
const int MAX_DISTANCE = 200;

NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE);
AccelStepper motor[NUM_MOTOR + 1];

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
    Serial.begin(230400);
}

void loop() {
    delay(50);
    unsigned int distance = sonar.ping_cm();
    if (Serial.available()) {
        readline();
        next_substr();
        
        // C is a wonderful language. str == "string literal" is undefined.
        // Then again, strcmp() returns 0 when two strings equal.

        if (strcmp(substr, "INFO") == 0) {
            Serial.print("IDEN ");
            Serial.println(DEVICE_ID);
        } else if (strcmp(substr, "MOTOR") == 0) {
            next_substr();
            int motor_id = substr_to_int();
            next_substr();
            int steps = substr_to_int();

            if (motor_id < NUM_MOTOR) {
                motor[motor_id].move(steps);
            }
        }
    }
    Serial.println("DAT {\"mass\": [0, 2], \"dist\": [0, 1], \"accel\": [[-1, 2, 3]], \"motor\": [true, true, false]}");
}

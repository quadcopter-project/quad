const int DEV_ID = 0;
bool isOperating = false;

// MOTOR
#include <AccelStepper.h>
const int NUM_MOTOR = 3;
const int PUL_PIN[NUM_MOTOR] = {2, 4, 6};
const int DIR_PIN[NUM_MOTOR] = {3, 5, 7};

const int MOTOR_MAX_SPEED = 60;
const int MOTOR_ACCELERATION = 200;

AccelStepper motor[NUM_MOTOR];

// MOTOR algorithm parameters
const double DOWNWARD_SPEED = -60;
const double UPWARD_SPEED = 30;
const int LEVEL_TEST_STEP = -5;
const double DIST_TOLERANCE = 0.2;
const double ACCEL_TOLERANCE = 0.03; // translates to about 0.2 degs

// HC-SR04
#include <NewPing.h>
const int TRIG_PIN = 8;
const int ECHO_PIN = 9;
const int MAX_DISTANCE = 200;
NewPing sonar(TRIG_PIN, ECHO_PIN, MAX_DISTANCE);

// MMA8451: No config since it needs the I2C bus.
#include <Wire.h>
#include "Adafruit_MMA8451.h"
#include <Adafruit_Sensor.h>
Adafruit_MMA8451 mma = Adafruit_MMA8451();

// Utitilies for reading and parsing Serial input
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

void next_substr(char* _substr) {
    sublen = 0;
    while (pos < len) {
        if (str[pos] == ' ') {
            pos++;
            break;
        }
        _substr[sublen] = substr[sublen] = str[pos++];
        sublen++;
    }
    _substr[sublen] = substr[sublen] = '\0';
}

int substr_to_int() {
    int x = 0, val = 0, sgn = 1;
    if (substr[0] == '-') {
        sgn = -1;
        x++;
    }
    for (int i = x; i < sublen; i++) {
        val = val * 10 + (substr[i] - '0');
    }
    return sgn * val;
}

double substr_to_double() {
    double val = 0;
    int x = 0, sgn = 1, dec_point = sublen;
    if (substr[0] == '-') {
        sgn = -1;
        x++;
    }
    for (int i = x; i < sublen; i++) {
        if (substr[i] == '.') dec_point = i;
        else {
            val = val * 10 + (substr[i] - '0');
        }
    }
    
    for (int i = 0; i < sublen - (dec_point + 1); i++) {
        val = val / 10;
    }
    return val * sgn;
}


// sensor functions
inline double getDistance() { return double(sonar.ping()) / 2 * 0.0343; }

inline void getAccel(double* accel) {
    mma.read();
    sensors_event_t event;
    mma.getEvent(&event);
    accel[0] = event.acceleration.x;
    accel[1] = event.acceleration.y;
    accel[2] = event.acceleration.z;
}


// motor functions
inline void stop() { for (int i = 0; i < NUM_MOTOR; i++) motor[i].stop(); }

inline void run() { for (int i = 0; i < NUM_MOTOR; i++) motor[i].run(); }

inline bool isRunning() { 
    bool running = false;
    for (int i = 0; i < NUM_MOTOR; i++) {
        running |= motor[i].isRunning();
    }
}

inline void setSpeed(double speed) { for (int i = 0; i < NUM_MOTOR; i++) motor[i].setSpeed(speed); }

inline void runSpeed() { for (int i = 0; i < NUM_MOTOR; i++) motor[i].runSpeed(); }

inline void blockedRun() {
    while (isRunning()) {
        run();
    }
}

/*
Change height until the reading on the sonar exceeds a lim (a lower bound.)
For consistency, if it's lowered, then it will first lower below this lim, then raise until
the lim is hit.
*/
void _setHeight(double lim) {
    bool wasOperating = isOperating;
    isOperating = true;
    report();

    double dist = getDistance();
    // define distance from when the sensor _just_ starts to report that distance
    // as the drone is raised.
    if (dist >= lim) {
        setSpeed(DOWNWARD_SPEED);
        while (dist >= lim) {
            runSpeed();
            dist = getDistance();
            report();   // TODO: in a production version, this can be eliminated
            delay(50);  // for ultrasound echo to get ready
        }
    } 
    stop();
    blockedRun();

    level();

    // and now we are sure the drone is below specified height limit.
    setSpeed(UPWARD_SPEED);
    while (dist < lim) {
        runSpeed();
        dist = getDistance();
        report();
        delay(50);
    }
    stop();
    blockedRun();

    level();

    isOperating = false | wasOperating;
    report();
}

void level() {
    bool wasOperating = isOperating;    // in case level was called by another function that "operates."
    isOperating = true;
    report();

    double accel[3], z, z1;
    // TODO: once in a certain order might not be enough. Consider adding a while above tolerance statement.
    for (int i = 0; i < NUM_MOTOR; i++) {
        getAccel(accel);
        z = accel[2];

        motor[i].move(LEVEL_TEST_STEP);
        blockedRun();
        getAccel(accel);
        z1 = accel[2];
        if (z1 <= z) { // TODO: set error tolerance term here.
            // this axis is no good, revert.  
            motor[i].move(LEVEL_TEST_STEP);
            blockedRun();
        } else {
            motor[i].setSpeed(DOWNWARD_SPEED);
            // routine to maximise z-component.
            // During this process motors only allowed to move the drone downward.
            while (z1 > z) {
                z = z1;
                runSpeed();
                delay(20);
                z1 = accel[2];
                report();   // TODO: remove this in final version
            }
        }
    }

    flushInput();
    isOperating = false | wasOperating;
    report();
}

// BLOCKING: during this process the arduino refuses any new calls, but keeps reporting data to the host.
void setHeight(double lim) {
    bool wasOperating = isOperating;
    isOperating = true;
    report();

    double dist = getDistance();
    double accel[3];
    getAccel(accel);

    // TODO: This actually grants pm DIST_TOLERANCE. too much?
    while (abs(dist - lim) > DIST_TOLERANCE \
        || max(abs(accel[0]), abs(accel[1])) > ACCEL_TOLERANCE) {
        _setHeight(lim);
        getAccel(accel);
        dist = getDistance();
        report();
    }

    flushInput();
    isOperating = false | wasOperating;
    report();
}

inline void flushInput() { while (Serial.available()) Serial.read(); }

inline void report() {
    // ultrasound
    double distance = getDistance();
    
    // accelerometer
    double accel[3];
    getAccel(accel);

    // motor
    bool moving[NUM_MOTOR];
    for (int i = 0; i < NUM_MOTOR; i++) {
        // isOperating has overriding authority.
        moving[i] = motor[i].isRunning();
    }
     
    // formatted output
    Serial.print("{");
    
    Serial.print("\"motor\": [");
    Serial.print(moving[0]);
    for (int i = 1; i < NUM_MOTOR; i++) {
        Serial.print(", ");
        Serial.print(moving[i]);
    }

    Serial.print("], \"accel\": [[");
    Serial.print(accel[0]);
    for (int i = 1; i < 3; i++) {
        Serial.print(", ");
        Serial.print(accel[i], 3);
    }

    Serial.print("]], \"dist\": [");
    Serial.print(distance);

    Serial.print("], \"operating\": [");
    Serial.print(isOperating);
    Serial.println("]}");
}


void setup() {
    Serial.begin(230400);   // wasted an hour on this :)

    // initiailise the motors.
    for (int i = 0; i < NUM_MOTOR; i++) {
        motor[i] = AccelStepper(AccelStepper::DRIVER, PUL_PIN[i], DIR_PIN[i]);
        motor[i].setMaxSpeed(MOTOR_MAX_SPEED);
        motor[i].setAcceleration(MOTOR_ACCELERATION);
        motor[i].setCurrentPosition(0);
    }

    // initailise accelerometer.
    mma.begin();    // and another half an hour on this.
    mma.setRange(MMA8451_RANGE_2_G);
}

void loop() {
    if (Serial.available()) {
        readline();
        char substr[20];
        next_substr(substr);

        if (strcmp(substr, "IDEN") == 0) {
            Serial.print("IDEN "); Serial.println(DEV_ID);
        } else if (strcmp(substr, "MOTOR") == 0) {
             
        } else if (strcmp(substr, "LEVEL") == 0) {
            stop();
            blockedRun();
            level();
        } else if (strcmp(substr, "HEIGHT") == 0) {
            stop();
            blockedRun();
            double height = substr_to_double();
            setHeight(height);
        } else if (strcmp(substr, "STOP") == 0) {
            stop();
            blockedRun();
        }
    } 

    run();
    report();

}

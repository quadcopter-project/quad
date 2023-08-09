const int DEV_ID = 0;
bool isOperating = false;

// MOTOR
#include <AccelStepper.h>
const int NUM_MOTOR = 3;
const int PUL_PIN[NUM_MOTOR] = {2, 4, 6};
const int DIR_PIN[NUM_MOTOR] = {3, 5, 7};

const int MOTOR_MAX_SPEED = 200;
const int MOTOR_ACCELERATION = 200;

AccelStepper motor[NUM_MOTOR];

// MOTOR algorithm parameters
// level parameters
const int STARTING_DOWNWARD_STEP = 200;
const int MIN_DOWNWARD_STEP = 25;
const double ACCEL_TOLERANCE = 0.1; // translates to about 0.6 degs
// setHeight parameters
const double DIST_TOLERANCE = 0.2;
const double DOWNWARD_SPEED = -60;
const double UPWARD_SPEED = 30;

// HC-SR04
const int TRIG_PIN = 8;
const int ECHO_PIN = 9;

// MMA8451: No config since it needs the I2C bus.
#include <Wire.h>
#include "Adafruit_MMA8451.h"
#include <Adafruit_Sensor.h>
Adafruit_MMA8451 mma = Adafruit_MMA8451();
const int ACCEL_MEAN_REPEATS = 3;
const int ACCEL_DELAY = 500;    // so that system can settle down.

// Utitilies for reading and parsing Serial input
char str[20];
char substr[20];
int len = 0;
int sublen = 0;
int pos = 0;

void readline() {
    len = sublen = pos = 0;
    char ch = Serial.read();
    while (ch != '\n') {
        str[len++] = ch;
        ch = Serial.read();
    }
    str[len] = '\0';
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


// Ultrasound HC-SR04 functions
inline void initDistance() {
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
}

inline double getDistance() {
    // trigger sensor with a HIGH pulse of 10us
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(ECHO_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    double duration = pulseIn(ECHO_PIN, HIGH); // Time in microseconds
    double distance_cm = duration / 2 * 0.0343;
    return distance_cm;
}


// Accelerometer MMA8451 functions
inline void getAccel(double* accel) {
    mma.read();
    sensors_event_t event;
    mma.getEvent(&event);
    accel[0] = event.acceleration.x;
    accel[1] = event.acceleration.y;
    accel[2] = event.acceleration.z;
}

inline void getMeanAccel(double* accel) {
    delay(ACCEL_DELAY);
    accel[0] = accel[1] = accel[2] = 0;
    double _accel[3];
    for (int i = 0; i < ACCEL_MEAN_REPEATS; i++) {
        getAccel(_accel);
        for (int j = 0; j < 3; j++) {
            accel[j] += _accel[j];
        }
    }
    for (int i = 0; i < 3; i ++) {
        accel[i] /= ACCEL_MEAN_REPEATS;
    }
}


// motor functions
inline void stop() { for (int i = 0; i < NUM_MOTOR; i++) motor[i].stop(); }

inline void run() { for (int i = 0; i < NUM_MOTOR; i++) motor[i].run(); }

inline bool isRunning() { 
    bool running = false;
    for (int i = 0; i < NUM_MOTOR; i++) {
        running |= motor[i].isRunning();
    }
    return running;
}

inline void setSpeed(double speed) { for (int i = 0; i < NUM_MOTOR; i++) motor[i].setSpeed(speed); }

inline void runSpeed() { for (int i = 0; i < NUM_MOTOR; i++) motor[i].runSpeed(); }

inline void blockedRun() {
    isOperating = true;
    report();
    while (isRunning()) {
        run();

        if (Serial.available()) {
            readline();
            char substr[20];
            next_substr(substr);
            if (strcmp(substr, "STOP")) stop();
            
        }
    }
    isOperating = false;
    report();
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
    bool wasOperating = isOperating;
    isOperating = true;
    report();

    double accel[3], xy, xy1;
    getMeanAccel(accel);

    int downward_step = STARTING_DOWNWARD_STEP;
    bool success_flag = false;

    while ((abs(accel[0]) > ACCEL_TOLERANCE || abs(accel[1]) > ACCEL_TOLERANCE)) {
        for (int i = 0; i < NUM_MOTOR; i++) {
            getMeanAccel(accel);
            xy = sq(accel[0]) + sq(accel[1]);

            motor[i].move(-downward_step);
            blockedRun();
            getMeanAccel(accel);
            xy1 = sq(accel[0]) + sq(accel[1]);

            while (xy1 <= xy) {
                // only require this while statement to be executed once to show we still have space for optimisation at larger step.
                success_flag = true;
                xy = xy1;
                motor[i].move(-downward_step);
                blockedRun();
                getMeanAccel(accel);
                xy1 = sq(accel[0]) + sq(accel[1]);
            }
            motor[i].move(downward_step); // at this point we must have overshot.
            blockedRun();
        }
    
        // finer accuracy required.
        if (!success_flag) downward_step /= 2;

        // didn't work, give it a kick and retry.
        if (downward_step < MIN_DOWNWARD_STEP) {
            motor[random(0, 3)].move(random(200, 400));
            blockedRun();
            downward_step = STARTING_DOWNWARD_STEP;
        }

        success_flag = false;
        getMeanAccel(accel);
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
        moving[i] = motor[i].isRunning();
    }

    // formatted output
    Serial.print("DAT {");
    
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

    // initialise ultrasound sensor.
    initDistance();

    // initialise RNG with noise
    randomSeed(analogRead(0));
}

void loop() {
    if (Serial.available()) {
        readline();
        char substr[20];
        next_substr(substr);

        if (strcmp(substr, "IDEN") == 0) {
            Serial.print("IDEN "); Serial.println(DEV_ID);
        } else if (strcmp(substr, "MOVE") == 0) {
            for (int i = 0; i < NUM_MOTOR; i++) {
                next_substr(substr);
                long steps = substr_to_int();
                motor[i].move(steps);
            }
            blockedRun();
        } else if (strcmp(substr, "LEVEL") == 0) {
            stop();
            blockedRun();
            level();
        } else if (strcmp(substr, "HEIGHT") == 0) {
            stop();
            blockedRun();
            next_substr(substr);
            double height = substr_to_double();
            setHeight(height);
        } else if (strcmp(substr, "STOP") == 0) {
            stop();
            blockedRun();
        }
    } 

    run();
    report();
    delay(100);
}

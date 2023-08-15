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
const int STARTING_DOWNWARD_STEP = 100;
const int MIN_DOWNWARD_STEP = 10;
const double STEP_DIV_FACTOR = 2.5; // using funny numbers might help with the "granular" nature of dividing steps by 2
const double ACCEL_TOLERANCE = 0.15; // translates to about 0.9 degs
// setHeight parameters
const double DIST_TOLERANCE = 0.75;
const double QUICK_ADJUST_LIMIT = 4;
const double QUICK_ADJUST_UP_STEPS = 50;
const double QUICK_ADJUST_DOWN_STEPS = -50;
const double FINE_ADJUST_UP_STEPS = 10;
const double FINE_ADJUST_DOWN_STEPS = -10;

// HC-SR04
const int TRIG_PIN = 8;
const int ECHO_PIN = 9;

// MMA8451: No config since it needs the I2C bus.
#include <Wire.h>
#include "Adafruit_MMA8451.h"
#include <Adafruit_Sensor.h>
Adafruit_MMA8451 mma = Adafruit_MMA8451();
const int ACCEL_MEAN_REPEATS = 3;
const int ACCEL_DELAY = 1500;    // so that system can settle down.

// Utitilies for reading and parsing Serial input
const int MAX_STR_LEN = 50;
char str[MAX_STR_LEN];
char substr[MAX_STR_LEN];
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
    digitalWrite(TRIG_PIN, HIGH);
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

inline void move(int steps) { for (int i = 0; i < NUM_MOTOR; i++) motor[i].move(steps); }

inline void blockedRun() {
    bool wasOperating = isOperating;
    isOperating = true;
    report();
    while (isRunning()) {
        run();

        if (Serial.available()) {
            readline();
            char substr[20];
            next_substr(substr);
            // no need to call blockedRun() again below, since
            // we are still in while loop, so it will move til stop if needed.
            if (strcmp(substr, "STOP")) stop();
        }
    }
    isOperating = false | wasOperating;
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
        while (dist >= lim) {
            int steps = FINE_ADJUST_DOWN_STEPS;
            if (dist - lim > QUICK_ADJUST_LIMIT) steps = QUICK_ADJUST_DOWN_STEPS;
            move(steps);
            blockedRun();
            dist = getDistance();
            report();
        }
    } 

    // must be sure the drone is level, or else the below raising segment will overshoot.
    level();

    // and now we are sure the drone is below specified height limit.
    while (dist < lim) {
        int steps = FINE_ADJUST_UP_STEPS;
        if (dist + QUICK_ADJUST_LIMIT < lim) steps = QUICK_ADJUST_UP_STEPS;
        move(steps);
        blockedRun();
        dist = getDistance();
        report();
    }

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

            // this movement pattern pretty much ensures the height is constant.
            // credit goes to James for coming up with it.
            move(downward_step / 2);
            motor[i].move(-downward_step); // overwrite
            
            blockedRun();
            getMeanAccel(accel);
            xy1 = sq(accel[0]) + sq(accel[1]);

            while (xy1 <= xy) {
                // only require this while statement to be executed once to show we still have space for optimisation at larger step.
                success_flag = true;
                xy = xy1;

                move(downward_step / 2);
                motor[i].move(-downward_step);

                blockedRun();
                getMeanAccel(accel);
                xy1 = sq(accel[0]) + sq(accel[1]);
            }
            // at this point we must have overshot.
            move(-downward_step / 2);
            motor[i].move(downward_step);
            blockedRun();
        }
    
        // finer accuracy required.
        if (!success_flag) downward_step /= STEP_DIV_FACTOR;

        // didn't work, give it a kick and retry.
        if (downward_step < MIN_DOWNWARD_STEP) {
            int random_step = -random(200, 400);
            move(-random_step / 2);
            motor[random(0, 3)].move(random_step);
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
        delay(ACCEL_DELAY * 2); // for platform to settle down
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

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
const int STARTING_DOWNWARD_STEP = 100; // stepsize for initial levelling attemps
const int MIN_DOWNWARD_STEP = 10; // smallest stepsize for levelling attempts
const double STEP_DIV_FACTOR = 2.5; // factor to divide current stepsize by to get stepsize for finer levelling
const double ACCEL_TOLERANCE = 0.15; // ..in the horizontal component. translates to about 0.9 degs
// _setHeight parameters
const double DIST_TOLERANCE = 0.75; // allowed deviation of measured height to target height
const double QUICK_ADJUST_LIMIT = 4; // min distance between measured & target before fine adjustment is used
const double QUICK_ADJUST_UP_STEPS = 50; // stepsize for quick adjustment going upwards
const double QUICK_ADJUST_DOWN_STEPS = -50;
const double FINE_ADJUST_UP_STEPS = 10;
const double FINE_ADJUST_DOWN_STEPS = -10; // stepsize for fine adjustment going downwards

// HC-SR04
const int TRIG_PIN = 8;
const int ECHO_PIN = 9;

// MMA8451: No config since it needs the I2C bus.
#include <Wire.h>
#include "Adafruit_MMA8451.h"
#include <Adafruit_Sensor.h>
Adafruit_MMA8451 mma = Adafruit_MMA8451();
sensors_event_t event;  // accelerometer readout data
const int ACCEL_MEAN_REPEATS = 20;  // average out oscillations
const int ACCEL_DELAY = 3000;    // so that system can settle down

// Utitilies for reading and parsing Serial input
const int MAX_STR_LEN = 50;
char str[MAX_STR_LEN + 5]; // readline() stores the line here
char substr[MAX_STR_LEN + 5]; // next_substr() stores its result here
int len = 0; // length of str[]
int sublen = 0; // length of substr[]
int pos = 0; // position on str[], used in next_substr() to determine where to begin again


// I/O FUNCTIONS
// read a line from Serial into str[]. Use of the String class, or default read methods is avoided.
void readline() {
    len = sublen = pos = 0;
    char ch = Serial.read();
    while (ch != '\n' && len < MAX_STR_LEN) {
        str[len++] = ch;
        ch = Serial.read();
    }
    str[len] = '\0';
}

// obtain the next substring in str[], using space as separator, and save it to substr[]
void next_substr() {
    sublen = 0;
    while (pos < len) {
        if (str[pos] == ' ') {
            pos++;
            break;
        }
        substr[sublen++] = str[pos++];
    }
    substr[sublen] = '\0';
}

// attempt a conversion of substr[] to an int value.
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

// attempt conversion of substr[] to a double value.
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

inline void flushInput() { while (Serial.available()) Serial.read(); }

// report current reading & status (isOperating).
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
    Serial.print(F("DAT {"));
    
    Serial.print(F("\"motor\": ["));
    Serial.print(moving[0]);
    for (int i = 1; i < NUM_MOTOR; i++) {
        Serial.print(F(", "));
        Serial.print(moving[i]);
    }

    Serial.print(F("], \"accel\": [["));
    Serial.print(accel[0]);
    for (int i = 1; i < 3; i++) {
        Serial.print(F(", "));
        Serial.print(accel[i], 3);
    }

    Serial.print(F("]], \"dist\": ["));
    Serial.print(distance);

    Serial.print(F("], \"operating\": ["));
    Serial.print(isOperating);
    Serial.println(F("]}"));
}


// ULTRASOUND HC-SR04 FUNCTIONS
// sensor initialization
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


// ACCELEROMETER MMA8451 FUNCTIONS
// obtain and unpack acceleration from library, then store to accel[], the passed in array.
inline void getAccel(double accel[]) {
    mma.read();
    mma.getEvent(&event);
    accel[0] = event.acceleration.x;
    accel[1] = event.acceleration.y;
    accel[2] = event.acceleration.z;
}

// obtain averaged acceleration by parameters specified at the top then store to array passed.
inline void getMeanAccel(double accel[]) {
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


// MOTOR FUNCTIONS
// most of these are but wrappers around underlying AccelStepper methods, acting on all motors at once.
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

inline void move(long steps) { for (int i = 0; i < NUM_MOTOR; i++) motor[i].move(steps); }

// Have the motors run and block the main thread while doing so until motors stop.
inline void blockedRun() {
    bool wasOperating = isOperating;
    isOperating = true;
    report();
    while (isRunning()) {
        run();

        if (Serial.available()) {
            readline();
            next_substr();
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

/*
Level by opportunistically lowering one of the three motors while raising the
other two.  

The lowering is attempted on each motor. If as a result the levelling is worse,
then revert.  

If at the same stepsize, all three motors fail to improve the result, the
stepsize is decreased, and the same procedure repeated, until a lower limit is
hit. When that happens a random motor is given a random "kick", and the whole
procedure repeated.

"Level of levelness" is measured by the horizontal component of the averaged
accelerometer reading.

BLOCKING: during this process the arduino refuses any new calls, but keeps
reporting data to the host.
*/
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
                // only require this while statement to be executed once to show
                // we still have space for optimisation at larger step.
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

// set the height to >= lim, then attempt levelling.
// Repeat this procedure until all tolerance constraints are met.
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
        next_substr();

        // the "protocol"
        if (strcmp(substr, "IDEN") == 0) {
            Serial.print(F("IDEN ")); Serial.println(DEV_ID);
        } else if (strcmp(substr, "MOVE") == 0) {
            for (int i = 0; i < NUM_MOTOR; i++) {
                next_substr();
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
            next_substr();
            double height = substr_to_double();
            setHeight(height);
        } else if (strcmp(substr, "STOP") == 0) {
            stop();
            blockedRun();
        }
    } 

    run();
    report();
    delay(200);

    // attempting reconnection if disconnected
    if(!Serial) {
        Serial.end();
        delay(200);
        Serial.begin(230400);
    }
}

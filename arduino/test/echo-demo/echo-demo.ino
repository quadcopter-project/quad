// HC-SR04
const int TRIG_PIN = 8;
const int ECHO_PIN = 9;

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

void setup() {
    initDistance();
    Serial.begin(230400);
}

void loop() {
    Serial.println(getDistance());
    delay(200);
}

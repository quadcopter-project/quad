const int DEV_ID = 4;
bool isOperating = false;


// RPM MEASUREMENT
const int rpm_factor = 30;
const int inputPin1 = 2;  // Digital pin for frequency input
unsigned long lastRisingEdge1 = 0;
unsigned long interval1 = 0;
float frequency1 = 0;

const int inputPin2 = 3;  // Digital pin for frequency input
unsigned long lastRisingEdge2 = 0;
unsigned long interval2 = 0;
float frequency2 = 0;

float rpm1 = 0;
float rpm2 = 0;

// only run during reporting to save resources
void rpm_update_and_report() {
  if (interval1 > 0) {
    frequency1 = 1000000.0 / interval1;  // Convert microseconds to Hz
  } else {
    frequency1 = 0;  // No signal detected
  }
  if (interval2 > 0) {
    frequency2 = 1000000.0 / interval2;  // Convert microseconds to Hz
  } else {
    frequency2 = 0;  // No signal detected
  }
  rpm1 = frequency1 * rpm_factor;
  rpm2 = frequency2 * rpm_factor;
  Serial.print(F("DAT {"));
  Serial.print(F("\"rpm1\": ["));
  Serial.print(rpm1);
  Serial.print(F("], \"rpm2\": ["));
  Serial.print(rpm2);
  Serial.print(F("], \"operating\": ["));
  Serial.print(isOperating);
  Serial.println(F("]}"));

}

//utils

const int MAX_STR_LEN = 50;
char str[MAX_STR_LEN + 5];
char substr[MAX_STR_LEN + 5];
int len = 0;
int sublen = 0;
int pos = 0;

void readline() {
    len = sublen = pos = 0;
    char ch = Serial.read();
    while (ch != '\n' && len < MAX_STR_LEN) {
        str[len++] = ch;
        ch = Serial.read();
    }
    str[len] = '\0';
}

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
void risingEdgeDetected1() {
  unsigned long currentTime = micros();
  interval1 = currentTime - lastRisingEdge1;
  lastRisingEdge1 = currentTime;
}
void risingEdgeDetected2() {
  unsigned long currentTime = micros();
  interval2 = currentTime - lastRisingEdge2;
  lastRisingEdge2 = currentTime;
}


void setup() {
  Serial.begin(230400);  // Initialize serial communication
  // attaching interrupt functions
  pinMode(inputPin1, INPUT);
  attachInterrupt(digitalPinToInterrupt(inputPin1), risingEdgeDetected1, RISING);
  pinMode(inputPin2, INPUT);
  attachInterrupt(digitalPinToInterrupt(inputPin2), risingEdgeDetected2, RISING);
}


void loop() {
  if (Serial.available()) {
    readline();
    next_substr();
    if (strcmp(substr, "IDEN") == 0) {
    Serial.print(F("IDEN "));
    Serial.println(DEV_ID);
    }
  }

  rpm_update_and_report();
  
  delay(200);
}



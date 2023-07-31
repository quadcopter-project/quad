const int DEV_ID = 2;
bool isOperating = false;

// Load cell
#include "HX711.h"
const int NUM_CELLS = 6;
const int LOADCELL_DOUT_PIN_0 = 3;
const int LOADCELL_SCK_PIN_0 = 2;
const double CALIB_FACTOR[NUM_CELLS] = {16660, 16660, 16660, 16660, 16660, 16660};

HX711 scales[NUM_CELLS];

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


// load cell functions
void get_units(double* mass) {
    for (int i = 0; i < NUM_CELLS; i++) {
        mass[i] = scales[i].get_units();
    }
}

inline void tare() { 
    isOperating = true;
    report();
    for (int i = 0; i < NUM_CELLS; i++) scales[i].tare(); 
    isOperating = false;
    report();
}

inline void set_scale() { for (int i = 0; i < NUM_CELLS; i++) scales[i].set_scale(CALIB_FACTOR[i]); }

// I/O functions
inline void flushInput() { while (Serial.available()) Serial.read(); }

inline void report() {
    // get mass readings
    double mass[NUM_CELLS];
    get_units(mass);

    // formatted output
    Serial.print("{");
    
    Serial.print("\"mass\": [");
    Serial.print(mass[0]);
    for (int i = 1; i < NUM_CELLS; i++) {
        Serial.print(", ");
        Serial.print(mass[i]);
    }

    Serial.print("], \"operating\": [");
    Serial.print(isOperating);
    Serial.println("]}");
}


void setup() {
    Serial.begin(230400);
    
    for (int i = 0; i < NUM_CELLS; i++) {
        HX711& scale = scales[i];
        scale.begin(LOADCELL_DOUT_PIN_0 + i * 2, LOADCELL_SCK_PIN_0 + i * 2);
    }
    set_scale();
    tare();
}

void loop() {
    if (Serial.available()) {
        readline();
        char substr[20];
        next_substr(substr);

        if (strcmp(substr, "IDEN") == 0) {
            Serial.print("CALIB");
            for (int i = 0; i < NUM_CELLS; i++) {
                Serial.print(" ");
                Serial.print(CALIB_FACTOR[i]);
            }

            Serial.print("IDEN ");
            Serial.println(DEV_ID);

        } else if (strcmp(substr, "TARE") == 0) {
            tare();
        }
    }

    report();

}

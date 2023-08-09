char str[20], substr[20];
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

void setup() {
    Serial.begin(9600);
}

void loop() {
    if (Serial.available()) {
        readline();
        char substr[20];
        next_substr(substr);
        next_substr(substr);
        Serial.println(substr_to_int());
    }
    delay(100);
}

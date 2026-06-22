const int OPT_PIN = 2;

volatile unsigned long zeroCrossUs = 0;
volatile unsigned long fireUs = 0;
volatile bool newReading = false;
unsigned long lastReadingMs = 0;

//const unsigned long TIMEOUT_MS = 50;  // ~3 cycles at 60Hz
const unsigned long TIMEOUT_MS = 20;  // ~3 cycles at 60Hz

unsigned int num_cycles = 0;
unsigned long last_reset = 0;

const unsigned long ZERO_BRIGHTNESS_NS = 1688220;
const unsigned long FULL_BRIGHTNESS_NS = 5944310;

void onAcChange() {
  if (digitalRead(OPT_PIN) == HIGH) {
    zeroCrossUs = micros();
    newReading = true;
  } else {
    fireUs = micros();
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(OPT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(OPT_PIN), onAcChange, CHANGE);
}

void loop() {
  if (newReading) {
    newReading = false;
    lastReadingMs = millis();

    if (zeroCrossUs < fireUs) return;

    unsigned long onTimeUs = zeroCrossUs - fireUs;
    num_cycles ++;

    float brightness = constrain( ((float)onTimeUs*1000 - ZERO_BRIGHTNESS_NS)/(FULL_BRIGHTNESS_NS-ZERO_BRIGHTNESS_NS), 0.0f, 1.0f);
    if (num_cycles > 5) {
        Serial.print(brightness, 8);
        Serial.println("");
        num_cycles = 0;
    }

  } else if (millis() - lastReadingMs > TIMEOUT_MS) {
    lastReadingMs = millis();  // reset to avoid spamming
    zeroCrossUs = micros();
    fireUs = zeroCrossUs;
    newReading = true;
  }
}


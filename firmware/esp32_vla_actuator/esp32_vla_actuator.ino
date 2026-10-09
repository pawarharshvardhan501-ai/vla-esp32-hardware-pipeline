#include <Arduino.h>
#include <ESP32Servo.h>

// --- Pin Definitions ---
#define SERVO_PIN     13
#define LED_RED_PIN   18
#define LED_GREEN_PIN 19
#define LED_BLUE_PIN  21

// --- Settings ---
Servo vlaServo;
const unsigned long SERIAL_TIMEOUT_MS = 1000; // Safety cutoff if Python disconnects
const float EMA_ALPHA = 0.5;                   // Moderate smoothing (Python already smooths)

// --- State Variables ---
unsigned long lastPacketTime = 0;
float currentSmoothedAngle = 90.0;
char serialBuffer[64];
size_t bufferIndex = 0;

void setup() {
  Serial.begin(115200);

  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);

  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_BLUE_PIN, LOW);

  ESP32PWM::allocateTimer(0);
  vlaServo.setPeriodHertz(50);
  vlaServo.attach(SERVO_PIN, 500, 2400);
  vlaServo.write(90);

  lastPacketTime = millis();
  Serial.println("[ESP32] Ready for VLA Telemetry Payload.");
}

void processIncomingCommand(char* cmd) {
  int targetAngle = 90;
  int r = 0, g = 0, b = 0;

  // Print raw incoming line to Serial Monitor for debugging
  Serial.print("[ESP32 RAW]: ");
  Serial.println(cmd);

  // Exact protocol matching: "ANGLES:90|LEDS:1,0,0"
  if (sscanf(cmd, "ANGLES:%d|LEDS:%d,%d,%d", &targetAngle, &r, &g, &b) == 4) {
    
    // Clamp constraints
    targetAngle = constrain(targetAngle, 0, 180);
    r = (r != 0) ? HIGH : LOW;
    g = (g != 0) ? HIGH : LOW;
    b = (b != 0) ? HIGH : LOW;

    // Apply light motion smoothing
    currentSmoothedAngle = (EMA_ALPHA * targetAngle) + ((1.0 - EMA_ALPHA) * currentSmoothedAngle);

    if (!vlaServo.attached()) {
      vlaServo.attach(SERVO_PIN, 500, 2400);
    }

    vlaServo.write((int)round(currentSmoothedAngle));

    // Actuate LEDs
    digitalWrite(LED_RED_PIN, r);
    digitalWrite(LED_GREEN_PIN, g);
    digitalWrite(LED_BLUE_PIN, b);

    lastPacketTime = millis();
  } else {
    Serial.println("[ESP32 ERROR]: Malformed Packet Format.");
  }
}

void readSerialData() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        serialBuffer[bufferIndex] = '\0'; // Safe null termination
        processIncomingCommand(serialBuffer);
        bufferIndex = 0;
      }
    } else {
      if (bufferIndex < sizeof(serialBuffer) - 1) {
        serialBuffer[bufferIndex++] = c;
      } else {
        bufferIndex = 0; // Buffer overflow safety reset
      }
    }
  }
}

void checkSafetyTimeout() {
  if (vlaServo.attached() && (millis() - lastPacketTime > SERIAL_TIMEOUT_MS)) {
    vlaServo.detach(); // Freezes servo to prevent motor coil burnout
    digitalWrite(LED_RED_PIN, LOW);
    digitalWrite(LED_GREEN_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
  }
}

void loop() {
  readSerialData();
  checkSafetyTimeout();
}

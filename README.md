## Hardware Connections & Pinout Guide

### System Architecture Overview### Pinout Mapping

| ESP32 Pin | Connected Component | Function / Signal Type |
| :--- | :--- | :--- |
| **GPIO 13** | Servo Motor Signal (Yellow/Orange Wire) | PWM Control Output |
| **GPIO 18** | Visual Status LED (Anode / (+) Leg) | Digital Target Detection Output |
| **GND** | Servo GND (Brown Wire) & LED GND | Common Ground |
| **5V / VIN** | Servo VCC (Red Wire) | 5V Servo Power Supply |

> **Hardware Safety Note:** Ensure the ESP32 and host machine share a common ground. If using external power for higher-torque servos, keep the GND lines tied together to prevent floating serial/PWM references.

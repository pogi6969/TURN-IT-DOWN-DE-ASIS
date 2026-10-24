// OVERPOWERED AMPHIBOAT - Arduino Nano
// FlySky FS-i6 + FS-iA6B (iBUS) -> 2 fan ESCs + 2 BTS7960 wheel drivers.
// iBUS signal -> D0 (RX). Unplug it while uploading.
//
// Sticks (mode 2): CH1 right X = steer, CH2 right Y = wheels, CH3 left Y = fans,
// CH5 SwA = arm fans (fans only arm with the fan stick at minimum),
// CH6 VrA = wheel power limit.
#include <Servo.h>

const int ESC_L = 9, ESC_R = 10;                  // fan ESC signals
const int LF = 5, LB = 6, RF = 3, RB = 11;        // BTS7960 RPWM/LPWM (R_EN, L_EN tied to 5 V)
const float WHEEL_MAX = 0.75;                     // 12 V motors on a 4S pack: cap at ~12.6 V
const float FAN_DIFF = 0.6;                       // differential thrust for steering
const unsigned long FAILSAFE_MS = 250;

Servo escL, escR;
uint16_t ch[14];
uint8_t buf[32];
uint8_t idx = 0;
unsigned long lastFrame = 0;
bool armed = false;

bool readIbus() {
  bool got = false;
  while (Serial.available()) {
    uint8_t b = Serial.read();
    if (idx == 0 && b != 0x20) continue;
    if (idx == 1 && b != 0x40) { idx = 0; continue; }
    buf[idx++] = b;
    if (idx == 32) {
      idx = 0;
      uint16_t sum = 0xFFFF;
      for (int i = 0; i < 30; i++) sum -= buf[i];
      if (sum == (buf[30] | (buf[31] << 8))) {
        for (int i = 0; i < 14; i++) ch[i] = buf[2 + 2 * i] | (buf[3 + 2 * i] << 8);
        got = true;
      }
    }
  }
  return got;
}

float stick(int i) { return constrain((ch[i] - 1500) / 500.0, -1.0, 1.0); }   // -1..1
float lever(int i) { return constrain((ch[i] - 1000) / 1000.0, 0.0, 1.0); }   // 0..1

void wheels(int fwdPin, int backPin, float v) {
  int pwm = (int)(constrain(fabs(v), 0.0, 1.0) * 255);
  analogWrite(fwdPin, v > 0.03 ? pwm : 0);
  analogWrite(backPin, v < -0.03 ? pwm : 0);
}

void allStop() {
  wheels(LF, LB, 0); wheels(RF, RB, 0);
  escL.writeMicroseconds(1000); escR.writeMicroseconds(1000);
  armed = false;
}

void setup() {
  Serial.begin(115200);
  pinMode(LF, OUTPUT); pinMode(LB, OUTPUT); pinMode(RF, OUTPUT); pinMode(RB, OUTPUT);
  escL.attach(ESC_L, 1000, 2000); escR.attach(ESC_R, 1000, 2000);
  allStop();
  delay(3000);                                    // ESCs arm on a minimum signal
}

void loop() {
  if (readIbus()) lastFrame = millis();
  if (millis() - lastFrame > FAILSAFE_MS) { allStop(); return; }

  float steer = stick(0), drive = stick(1), fan = lever(2);
  float limit = WHEEL_MAX * (0.4 + 0.6 * lever(5));
  float l = drive + steer, r = drive - steer;
  float k = max(1.0, max(fabs(l), fabs(r)));
  wheels(LF, LB, limit * l / k);
  wheels(RF, RB, limit * r / k);

  bool sw = ch[4] > 1600;
  if (!sw) armed = false;
  else if (!armed && fan < 0.05) armed = true;    // never arm with the throttle up
  float fl = 0, fr = 0;
  if (armed) {
    fl = constrain(fan * (1 + FAN_DIFF * steer), 0.0, 1.0);
    fr = constrain(fan * (1 - FAN_DIFF * steer), 0.0, 1.0);
  }
  escL.writeMicroseconds(1000 + (int)(fl * 1000));
  escR.writeMicroseconds(1000 + (int)(fr * 1000));
}

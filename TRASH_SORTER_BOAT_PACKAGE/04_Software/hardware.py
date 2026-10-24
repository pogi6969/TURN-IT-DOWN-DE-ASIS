"""Motors, servos and the item sensor. Falls back to print-only mocks when the
Raspberry Pi libraries are missing, so the app also runs on a laptop for testing."""
import logging
import threading

import config

log = logging.getLogger("hw")

try:
    from gpiozero import Motor, DigitalInputDevice
    ON_PI = True
except Exception:                      # not on a Pi
    ON_PI = False

try:
    from adafruit_servokit import ServoKit
except Exception:
    ServoKit = None


class _MockMotor:
    def __init__(self, name):
        self.name, self.value = name, 0.0

    def forward(self, speed=1.0):
        self.value = speed

    def backward(self, speed=1.0):
        self.value = -speed

    def stop(self):
        self.value = 0.0


class _MockSensor:
    def __init__(self):
        self.value = 0


def _motor(name, pins):
    if ON_PI:
        return Motor(pins["forward"], pins["backward"], enable=pins["enable"], pwm=True)
    return _MockMotor(name)


def _set(motor, speed):
    speed = max(-1.0, min(1.0, speed))
    if speed > 0.02:
        motor.forward(speed)
    elif speed < -0.02:
        motor.backward(-speed)
    else:
        motor.stop()


class Hardware:
    def __init__(self):
        self.left = _motor("left", config.DRIVE_LEFT)
        self.right = _motor("right", config.DRIVE_RIGHT)
        self.c1 = _motor("c1", config.C1_PINS)
        self.c2 = _motor("c2", config.C2_PINS)
        self.ir = DigitalInputDevice(config.IR_PIN, pull_up=config.IR_ACTIVE_LOW) if ON_PI else _MockSensor()
        self.kit = ServoKit(channels=16) if (ON_PI and ServoKit) else None
        self.servo_angle = {}
        self._lock = threading.Lock()
        for b in config.SERVO_CHANNELS:
            self.flap(b, False)

    # drive ------------------------------------------------------------------
    def drive(self, x, y):
        """Joystick x (right +) and y (forward +), each -1..1 -> tank steering."""
        x, y = x * config.TURN_GAIN, y
        left, right = y + x, y - x
        k = max(1.0, abs(left), abs(right))
        _set(self.left, config.DRIVE_MAX * left / k)
        _set(self.right, config.DRIVE_MAX * right / k)

    def stop_drive(self):
        _set(self.left, 0)
        _set(self.right, 0)

    # conveyors --------------------------------------------------------------
    def conveyor(self, which, speed):
        _set(self.c1 if which == 1 else self.c2, speed)

    # sensor -----------------------------------------------------------------
    def item_present(self):
        v = bool(self.ir.value)
        return v                        # gpiozero inverts with pull_up=True, so 1 = item

    # flaps ------------------------------------------------------------------
    def flap(self, bin_no, open_):
        angle = (config.SERVO_OPEN if open_ else config.SERVO_CLOSED)[bin_no]
        with self._lock:
            self.servo_angle[bin_no] = angle
            if self.kit:
                self.kit.servo[config.SERVO_CHANNELS[bin_no]].angle = angle
            else:
                log.debug("flap %s -> %s deg", bin_no, angle)

    def all_stop(self):
        self.stop_drive()
        self.conveyor(1, 0)
        self.conveyor(2, 0)

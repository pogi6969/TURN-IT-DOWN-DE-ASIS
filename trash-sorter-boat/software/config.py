"""All tunable numbers in one place. Pin numbers are BCM GPIO numbers."""

# --- network / dashboard --------------------------------------------------
HTTP_PORT = 8080
DRIVE_TIMEOUT_S = 0.8          # drive motors stop if the phone sends nothing for this long

# --- drive motors (L298N #1, left pair on A, right pair on B) --------------
DRIVE_LEFT = dict(forward=5, backward=6, enable=12)
DRIVE_RIGHT = dict(forward=20, backward=21, enable=13)
DRIVE_MAX = 1.0                # 0..1 PWM cap
TURN_GAIN = 0.8

# --- conveyors (L298N #2: C1 intake on A, C2 sorting belt on B) ------------
C1_PINS = dict(forward=23, backward=24, enable=18)
C2_PINS = dict(forward=16, backward=26, enable=19)
C1_SPEED = 0.8                 # 12 V JGA25-370 30 rpm -> ~64 mm/s belt at 0.8
C2_SPEED = 0.7                 # ~56 mm/s

# --- item sensor at the end of the camera zone -----------------------------
IR_PIN = 17                    # FC-51 OUT, LOW when an item is in front of it
IR_ACTIVE_LOW = True
SETTLE_S = 0.1                 # extra belt run after the trigger; raise it if items stop short of the lens

# --- flap servos on the PCA9685 --------------------------------------------
SERVO_CHANNELS = {1: 0, 2: 1, 3: 2, 4: 3}      # bin number -> PCA9685 channel
SERVO_CLOSED = {1: 90, 2: 90, 3: 90, 4: 90}    # degrees, trim after assembly
SERVO_OPEN = {1: 150, 2: 30, 3: 150, 4: 30}    # port flaps swing one way, starboard the other (60 deg)
# seconds of C2 travel needed after the flap opens, measured from the camera stop
TRAVEL_S = {1: 3.5, 2: 3.5, 3: 5.5, 4: 5.5}

# --- classifier (Google Teachable Machine -> Export -> TensorFlow Lite) ----
MODEL_PATH = "model/model_unquant.tflite"      # or model.tflite (quantized)
LABELS_PATH = "model/labels.txt"
VOTES = 5                      # frames classified per item
MIN_CONFIDENCE = 0.70          # below this the item goes to the "other" bin
EMPTY_LABEL = "Empty"          # train a class of the bare belt with this name
# class name (as typed in Teachable Machine) -> bin
LABEL_TO_BIN = {"Plastic bottle": 1, "Can": 2, "Paper": 3, "Other": 4}
FALLBACK_BIN = 4

# --- cameras ---------------------------------------------------------------
NAV_CAMERA_INDEX = 0           # USB webcam (/dev/video0)
NAV_SIZE = (640, 480)
SORT_SIZE = (640, 480)         # Pi camera on the CSI port

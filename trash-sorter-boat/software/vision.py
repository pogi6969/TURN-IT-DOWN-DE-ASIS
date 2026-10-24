"""Cameras and the trash classifier.

Navigation camera: USB webcam via OpenCV, streamed to the phone as MJPEG.
Sorting camera: Raspberry Pi camera via Picamera2, frames go to a TensorFlow
Lite model exported from Google Teachable Machine (image project, 224 x 224).
"""
import logging
import os
import threading
import time

import numpy as np

import config

log = logging.getLogger("vision")

try:
    import cv2
except Exception:
    cv2 = None
try:
    from picamera2 import Picamera2
except Exception:
    Picamera2 = None


def _load_interpreter(path):
    for mod in ("ai_edge_litert.interpreter", "tflite_runtime.interpreter", "tensorflow.lite"):
        try:
            m = __import__(mod, fromlist=["Interpreter"])
            return m.Interpreter(model_path=path)
        except Exception:
            continue
    raise RuntimeError("install ai-edge-litert (or tflite-runtime) to run the model")


class Classifier:
    def __init__(self, model_path=config.MODEL_PATH, labels_path=config.LABELS_PATH):
        self.labels = []
        with open(labels_path) as f:
            for line in f:
                parts = line.strip().split(" ", 1)          # Teachable Machine: "0 Plastic bottle"
                if parts and parts[0]:
                    self.labels.append(parts[1] if len(parts) == 2 and parts[0].isdigit() else line.strip())
        self.it = _load_interpreter(model_path)
        self.it.allocate_tensors()
        self.inp = self.it.get_input_details()[0]
        self.out = self.it.get_output_details()[0]
        self.size = tuple(self.inp["shape"][1:3])

    def predict(self, rgb):
        """rgb: HxWx3 uint8. Returns (label, confidence)."""
        h, w = self.size
        img = cv2.resize(rgb, (w, h)) if cv2 is not None else rgb[:h, :w]
        if self.inp["dtype"] == np.uint8:
            x = img.astype(np.uint8)[None]
        else:
            x = (img.astype(np.float32) / 127.5 - 1.0)[None]     # Teachable Machine normalisation
        self.it.set_tensor(self.inp["index"], x)
        self.it.invoke()
        y = self.it.get_tensor(self.out["index"])[0].astype(np.float32)
        if self.out["dtype"] == np.uint8:
            scale, zero = self.out.get("quantization", (1 / 255.0, 0))
            y = (y - zero) * scale
        i = int(np.argmax(y))
        return self.labels[i], float(y[i])


class SortCamera:
    def __init__(self):
        self.cam = None
        if Picamera2:
            self.cam = Picamera2()
            self.cam.configure(self.cam.create_still_configuration(main={"size": config.SORT_SIZE, "format": "RGB888"}))
            self.cam.start()
            time.sleep(1.0)

    def frame(self):
        if self.cam is None:
            return np.zeros((config.SORT_SIZE[1], config.SORT_SIZE[0], 3), np.uint8)
        return self.cam.capture_array()


class NavCamera:
    """Grabs frames in a thread; latest() returns the newest JPEG bytes."""

    def __init__(self):
        self._jpeg = None
        self._lock = threading.Lock()
        self.ok = False
        if cv2 is None:
            return
        self.cap = cv2.VideoCapture(config.NAV_CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.NAV_SIZE[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.NAV_SIZE[1])
        self.ok = self.cap.isOpened()
        if self.ok:
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            ok, img = self.cap.read()
            if not ok:
                time.sleep(0.1)
                continue
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                with self._lock:
                    self._jpeg = buf.tobytes()

    def latest(self):
        with self._lock:
            return self._jpeg


def save_training_image(rgb, label, root="dataset"):
    """Used by collect.py: saves a frame under dataset/<label>/."""
    d = os.path.join(root, label)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{int(time.time() * 1000)}.jpg")
    cv2.imwrite(path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return path

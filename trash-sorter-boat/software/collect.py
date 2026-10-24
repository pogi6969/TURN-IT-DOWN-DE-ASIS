"""Capture training photos from the sorting camera for Google Teachable Machine.

    python3 collect.py "Plastic bottle"      # press Enter for each photo, q + Enter to stop

Put each item on the belt under the lens, turn it between shots. Aim for 80+
photos per class, plus an "Empty" class of the bare belt. Then zip the
dataset/ folders, upload them to teachablemachine.withgoogle.com (Image
project), train, Export -> TensorFlow Lite -> Floating point, and copy
model_unquant.tflite + labels.txt into software/model/.
"""
import sys

import vision


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "Empty"
    cam = vision.SortCamera()
    n = 0
    while input(f"[{label}] {n} saved - Enter to shoot, q to quit: ").strip().lower() != "q":
        print(vision.save_training_image(cam.frame(), label))
        n += 1


if __name__ == "__main__":
    main()

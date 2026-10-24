#!/bin/bash
# One-time setup on Raspberry Pi OS (Bookworm, 64-bit) on a Raspberry Pi 4.
set -e
sudo apt update
sudo apt install -y python3-opencv python3-picamera2 python3-flask python3-numpy python3-gpiozero
sudo raspi-config nonint do_i2c 0                     # PCA9685 servo board
python3 -m venv --system-site-packages ~/boatenv
~/boatenv/bin/pip install adafruit-circuitpython-servokit ai-edge-litert
# Wi-Fi hotspot the phone joins (NetworkManager): SSID TRASHBOAT, password boat12345
sudo nmcli device wifi hotspot ssid TRASHBOAT password boat12345 || true
sudo nmcli connection modify Hotspot connection.autoconnect yes || true
# start the boat software on every boot
sed "s#/home/pi#$HOME#g; s#User=pi#User=$USER#" trashboat.service | sudo tee /etc/systemd/system/trashboat.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now trashboat
echo "Done. Join Wi-Fi TRASHBOAT and open http://10.42.0.1:8080"

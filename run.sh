#!/bin/sh

./makeconf.sh

echo "[Info] Run Wallpad Controller"
exec python3 main.py

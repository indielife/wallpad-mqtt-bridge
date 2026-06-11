#!/bin/sh

echo "[Info] Run Wallpad Controller"
./makeconf.sh
exec python3 -m kocom.main

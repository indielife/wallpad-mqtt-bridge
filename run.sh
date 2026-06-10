#!/bin/sh

SHARE_DIR=/share/kocom
mkdir -p $SHARE_DIR
cp -u /*.py $SHARE_DIR

/makeconf.sh

echo "[Info] Run Wallpad Controller"
cd $SHARE_DIR
python3 $SHARE_DIR/main.py

# for dev
# while true; do echo "still live"; sleep 100; done

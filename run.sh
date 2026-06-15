#!/bin/bash

export ADDON_VERSION=$(jq -r '.version' config.json)

echo "========================================================"
echo "    KOCOM Wallpad RS485 Controller Add-on"
echo "    Version: ${ADDON_VERSION}"
echo "========================================================"

exec python3 -m wallpad.main

#!/bin/bash

if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

rsync -avz --exclude '/.*' ./ "$HA_USER"@"$HA_IP":"$HA_PATH"

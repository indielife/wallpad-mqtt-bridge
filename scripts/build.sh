#!/bin/bash

# 도커 이미지 빌드
docker build -t wallpad-mqtt-bridge .


# 도커 이미지 실행 - Socket 모드 (EW11 등 시리얼-네트워크 변환기 사용 시)
# scripts/options.example.json을 복사해 실제 IP/계정 정보를 채운 뒤 마운트합니다.

# docker run --rm -it \
#   -v "$(pwd)/scripts/options.json":/data/options.json \
#   wallpad-mqtt-bridge


# 도커 이미지 실행 - Serial 모드 (USB 직접 연결 시)
# /dev/ttyUSB0를 HA VM에서 제어권을 가져가기 때문에 실행할 수 없음

# docker run --rm -it \
#   --device=/dev/ttyUSB0:/dev/ttyUSB0 \
#   -v "$(pwd)/scripts/options.json":/data/options.json \
#   wallpad-mqtt-bridge


# 도커 로그 실시간 모니터링

# docker logs -f kocom-test

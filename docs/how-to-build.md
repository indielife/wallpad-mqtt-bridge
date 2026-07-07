# 로컬 빌드 및 테스트 가이드

## 전제 조건

- Docker 설치
- 월패드가 EW11 등 시리얼-네트워크 변환기를 통해 네트워크에 연결되어 있을 것 (Socket 모드)
- MQTT 브로커 접근 가능 (HA VM 내의 Mosquitto를 그대로 사용 가능)

## 이미지 빌드

```bash
docker build -t wallpad-mqtt-bridge .
```

## 설정 파일 준비

`scripts/options.example.json`을 복사해 실제 환경에 맞게 수정합니다.

```bash
cp scripts/options.example.json scripts/options.json
```

`scripts/options.json`에서 수정할 항목:

| 항목 | 위치 | 예시 |
|------|------|------|
| MQTT 브로커 IP | `MQTT Broker.Server` | `192.168.0.10` |
| MQTT 계정 | `MQTT Broker.Username / Password` | HA에서 설정한 값 |
| EW11 IP | `Wallpad.Socket.Server` | `192.168.0.11` |
| EW11 포트 | `Wallpad.Socket.Port` | `8899` |
| 활성화할 기기 | `Wallpad.Enabled Devices` | 필요한 항목만 `true` |

> `scripts/options.json`은 `.gitignore`에 추가해 실제 IP/비밀번호가 커밋되지 않도록 합니다.

## 컨테이너 실행 (Socket 모드)

```bash
docker run --rm -it \
  -v "$(pwd)/scripts/options.json":/data/options.json \
  wallpad-mqtt-bridge
```

로그 레벨을 `debug`로 설정하면 RS485 패킷 수신 내용을 실시간으로 확인할 수 있습니다.

## 셸로 진입해서 확인

```bash
docker run --rm -it \
  -v "$(pwd)/scripts/options.json":/data/options.json \
  wallpad-mqtt-bridge bash
```

## 참고: Serial 모드

USB 시리얼 젠더를 직접 우분투 호스트에 연결한 경우 `--device` 옵션으로 전달할 수 있습니다.
단, HA VM이 해당 USB 포트를 점유하고 있으면 동시에 사용할 수 없습니다.

```bash
docker run --rm -it \
  --device=/dev/ttyUSB0:/dev/ttyUSB0 \
  -v "$(pwd)/scripts/options.json":/data/options.json \
  wallpad-mqtt-bridge
```

# Kocom Wallpad Add-on for Home Assistant

## 지원 제조사 (Supported Manufacturers)

현재 이 애드온이 지원하는 월패드 제조사는 다음과 같습니다.
- **Kocom (코콤)**

## 설정 가이드 (Configuration)

애드온 설정 탭에서 다음과 같이 기본 설정 항목을 입력합니다.

### 1. MQTT Broker
홈어시스턴트에서 사용하는 MQTT 브로커(예: Mosquitto Broker 애드온)와의 연결 정보입니다.
- **Server**: MQTT 브로커가 동작 중인 서버 IP 주소 (예: `192.168.0.10`)
- **Username**: MQTT 사용자 계정 ID
- **Password**: MQTT 사용자 계정 비밀번호

### 2. Wallpad
월패드 제조사 및 연결 정보 설정입니다.
- **Manufacturer**: 월패드 제조사 명칭. 현재는 `kocom`만 지원됩니다. (기본값: `kocom`)
- **Connection Type**: 월패드와 통신하는 물리적인 연결 방식 선택 (`Serial` 또는 `Socket`)
  - `Serial`: RS485 라인이 USB 시리얼 젠더를 통해 홈어시스턴트 서버(라즈베리 파이, 미니PC 등)에 직접 연결되어 있는 경우 사용합니다.
  - `Socket`: RS485 라인이 EW11 등 시리얼-네트워크 변환기에 연결되어 네트워크를 통해 통신하는 경우 사용합니다.
- **Socket**: `Connection Type`을 `Socket`으로 설정한 경우 활성화되는 네트워크 연결 설정입니다.
  - **Server**: 시리얼-네트워크 변환기(예: Elfin EW11)의 IP 주소를 입력합니다. (예: `192.168.0.11`)
  - **Port**: 변환기에 설정한 소켓 포트 번호를 입력합니다. (기본값: `8899`)
- **Serial**: `Connection Type`을 `Serial`로 설정한 경우 활성화되는 시리얼 포트 설정입니다.
  - **Port**: 홈어시스턴트 서버에 연결된 USB 시리얼 디바이스 경로를 입력합니다. (예: `/dev/ttyUSB0`)

### 3. Enabled Devices
월패드 제어 대상 기기를 활성화하는 설정입니다. (활성화할 기기는 `true`로 설정)
- **light**: 조명
- **plug**: 플러그(대기전력콘센트)
- **thermostat**: 난방(온도조절기)
- **fan**: 환기팬
- **gas**: 가스 밸브
- **elevator**: 엘리베이터 호출

### 4. Ventilator
전열교환기(환기장치) 연동 설정입니다.
- **Manufacturer**: 전열교환기 제조사 선택 (`None`, `Grex` 중 선택. 기본값: `None`)
- **Connection Type**: 전열교환기 연결 방식 선택 (`Serial` 또는 `Socket`)
  - `Serial`: 전열교환기 통신선이 USB 시리얼 젠더를 통해 홈어시스턴트 서버에 직접 연결되어 있는 경우 사용합니다. (벽면 조절기용, 환기장치 본체용 총 2개의 시리얼 포트가 필요합니다.)
  - `Socket`: 전열교환기 통신선이 EW11 등 시리얼-네트워크 변환기에 연결되어 네트워크를 통해 통신하는 경우 사용합니다.
- **Serial**: `Connection Type`을 `Serial`로 설정한 경우 활성화되는 시리얼 포트 설정입니다.
  - **Controller Port**: 전열교환기 벽면 조절기 라인에 연결된 USB 시리얼 디바이스 경로를 입력합니다. (예: `/dev/ttyUSB1`)
  - **Ventilator Port**: 전열교환기 본체 라인에 연결된 USB 시리얼 디바이스 경로를 입력합니다. (예: `/dev/ttyUSB2`)
- **Socket**: `Connection Type`을 `Socket`으로 설정한 경우 활성화되는 네트워크 연결 설정입니다.
  - **Server**: 시리얼-네트워크 변환기(예: Elfin EW11)의 IP 주소를 입력합니다. (예: `192.168.0.12`)
  - **Port**: 변환기에 설정한 소켓 포트 번호를 입력합니다. (기본값: `8899`)
- **Default Speed**: 기본 환기 속도 선택 (`low`, `medium`, `high` 등. 기본값: `low`)

## 문서 (Documentation)

프로젝트에 대한 상세한 가이드는 다음 문서들을 참고하세요.

- [시스템 아키텍처 가이드](docs/architecture.md): MQTT-RS485 브릿지의 핵심 컴포넌트와 패킷 흐름을 다룹니다.
- [하드웨어 연결 가이드](docs/hardware_connection.md): RS485 통신 방식(소켓/시리얼) 및 기기별 결선 아키텍처(버스/프록시)를 설명합니다.
- [로컬 개발 가이드](docs/development.md): `uv`를 사용한 로컬 가상환경 구성, 패키지 관리, 포매팅/린트 설정 및 도커 빌드 검증 방법을 설명합니다.
- [코콤 패킷 분석 가이드](docs/packet_analysis.md): 코콤 월패드 통신 패킷 구조 및 각 디바이스별 Hex 코드 정의를 설명합니다.

## Credits & Acknowledgements

이 프로젝트는 [Zoolian/zooil]님의 [kocomRS485](https://github.com/zooil/kocomRS485) 프로젝트를 기반으로 새롭게 구성하고 수정한 버전입니다.
좋은 코드를 공유해 주신 원작자분께 감사드립니다.

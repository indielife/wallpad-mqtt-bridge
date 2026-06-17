# Kocom Wallpad Add-on for Home Assistant

## 지원 제조사 (Supported Manufacturers)

현재 이 애드온이 지원하는 월패드 제조사는 다음과 같습니다.
- **Kocom (코콤)**

## 설정 가이드 (Configuration)

애드온 설정 탭에서 다음과 같이 기본 설정 항목을 입력합니다.

### 1. MQTT Broker
MQTT 브로커 연결 정보입니다.
- **Server**: MQTT 브로커 IP 주소 (예: `192.168.0.10`)
- **Username**: MQTT 사용자 계정 ID
- **Password**: MQTT 사용자 계정 비밀번호

### 2. Wallpad
월패드 제조사 및 연결 정보 설정입니다.
- **Manufacturer**: 월패드 제조사 명칭. 현재는 `kocom`만 지원됩니다. (기본값: `kocom`)
- **Connection Type**: 월패드 연결 방식 (`Serial` 또는 `Socket`)
- **Socket**: 소켓 연결(네트워크) 시 주소 및 포트 설정
  - **Server**: 소켓 서버 IP 주소 (예: `192.168.0.11`)
  - **Port**: 소켓 서버 포트 번호 (기본값: `8899`)
- **Serial**: 시리얼 연결 시 포트 설정
  - **Port**: 시리얼 디바이스 포트 경로 (예: `/dev/ttyUSB0`)

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
- **Connection Type**: 전열교환기 연결 방식 (`Serial` 또는 `Socket`)
- **Serial**: 시리얼 연결 시 포트 경로 설정 (`Controller Port`, `Ventilator Port`)
- **Socket**: 소켓 연결 시 서버 주소 및 포트 설정 (`Server`, `Port`)
- **Default Speed**: 기본 환기 속도 (`low`, `medium`, `high` 등)

## 문서 (Documentation)

프로젝트에 대한 상세한 가이드는 다음 문서들을 참고하세요.

- [시스템 아키텍처 가이드](docs/architecture.md): MQTT-RS485 브릿지의 핵심 컴포넌트와 패킷 흐름을 다룹니다.
- [하드웨어 연결 가이드](docs/hardware_connection.md): RS485 통신 방식(소켓/시리얼) 및 기기별 결선 아키텍처(버스/프록시)를 설명합니다.
- [로컬 개발 가이드](docs/development.md): `uv`를 사용한 로컬 가상환경 구성, 패키지 관리, 포매팅/린트 설정 및 도커 빌드 검증 방법을 설명합니다.
- [코콤 패킷 분석 가이드](docs/packet_analysis.md): 코콤 월패드 통신 패킷 구조 및 각 디바이스별 Hex 코드 정의를 설명합니다.

## Credits & Acknowledgements

이 프로젝트는 [Zoolian/zooil]님의 [kocomRS485](https://github.com/zooil/kocomRS485) 프로젝트를 기반으로 새롭게 구성하고 수정한 버전입니다.
좋은 코드를 공유해 주신 원작자분께 감사드립니다.

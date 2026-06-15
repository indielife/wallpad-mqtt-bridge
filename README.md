# Kocom Wallpad Add-on for Home Assistant

## 문서 (Documentation)

프로젝트에 대한 상세한 가이드는 다음 문서들을 참고하세요.

- [시스템 아키텍처 가이드](docs/architecture.md): MQTT-RS485 브릿지의 핵심 컴포넌트와 패킷 흐름을 다룹니다.
- [하드웨어 연결 가이드](docs/hardware_connection.md): RS485 통신 방식(소켓/시리얼) 및 기기별 결선 아키텍처(버스/프록시)를 설명합니다.
- [로컬 개발 가이드](docs/development.md): `uv`를 사용한 로컬 가상환경 구성, 패키지 관리, 포매팅/린트 설정 및 도커 빌드 검증 방법을 설명합니다.
- [코콤 패킷 분석 가이드](docs/packet_analysis.md): 코콤 월패드 통신 패킷 구조 및 각 디바이스별 Hex 코드 정의를 설명합니다.

## Credits & Acknowledgements

이 프로젝트는 [Zoolian/zooil]님의 [kocomRS485](https://github.com/zooil/kocomRS485) 프로젝트를 기반으로 새롭게 구성하고 수정한 버전입니다.
좋은 코드를 공유해 주신 원작자분께 감사드립니다.

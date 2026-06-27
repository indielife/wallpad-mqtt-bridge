<!-- [IMPORTANT] 이 파일을 .gitignore에 추가하지 말 것. 이 파일을 절대 git add 하지 말 것 -->

# TO-BE
```
wallpad/
  panel/              ← Kocom 클래스 → 공통 WallpadPanel로 (기기 관리, HA 연동)
    panel.py
    state.py
    devices/          ← 기기별 HA 엔티티 정의 (light, fan... 제조사 무관)
  ventilator/         ← Grex 클래스 → 공통 Ventilator로 (팬 관리, HA 연동)
    ventilator.py
    devices/
  protocol/           ← 제조사별 패킷 처리 전담
    base.py           ← 공통 인터페이스 (start_byte, packet_len, parse, build...)
    kocom/
      constants.py    ← hex 매핑
      packet_builder.py
      protocol.py     ← KocomProtocol(base.py 구현)
    grex/
      constants.py    ← MODE/SPEED hex
      packet_builder.py
      protocol.py     ← GrexProtocol(base.py 구현)
  transport/
  mqtt/
  devices/            ← 공통 베이스 클래스 (그대로)
```

# Phase

[x] Phase 1 (작음) — 지금 당장 가능
  - hex 상수 + 패킷 빌더만 protocol/ 로 이동
  - 기존 동작 변화 없이 파일 위치만 정리

[ ] Phase 2 (중간) — 다른 제조사 선행조사 후
  - protocol/base.py 인터페이스 설계
  - 파싱 로직을 protocol 레이어로 이전

[ ] Phase 3 (큰) — Phase 2 검증 후
  - panel/, ventilator/ 공통 클래스화
  - main.py 팩토리 패턴 연결


# 2026-06-23 Gemini 의견

1. 베이스 코드 없이 처음부터 설계했다면? (방향성 검토)
현재 진행 중인 리팩토링 방향은 올바른 방향입니다. WallpadPanel이 각 기기의 세부적인 토픽 조합 형태나 라우팅 로직을 모두 알고 있던 강결합 구조를 해제하고, 기기에 토픽과 상태 파싱 책임을 위임하여 결합도를 낮추는 객체지향적인 정석 리팩토링입니다.

만약 베이스 코드 없이 처음부터 아예 새로 설계했더라면, 각 디바이스를 파이썬 클래스(OOP)로 복잡하게 쪼개기보다 선언적(Declarative) 매핑 방식을 선택했을 것입니다.

예: config.yaml이나 데이터 매핑 테이블(JSON)에 각 기기 타입별 HA 컴포넌트 정보, MQTT 토픽 템플릿, RS485 패킷 인덱스를 적어두고, 단일 MqttBridge 엔진이 이를 해석해 라우팅과 메시지 발행을 일괄 처리하게 만들었을 것입니다. 이렇게 하면 새 장치를 추가할 때 파이썬 코드를 수정할 필요 없이 설정만 추가하면 됩니다.
하지만 점진적으로 기존 코드를 리팩토링하는 현재 상황에서는 코드 안정성을 지키면서 유연함을 확보하기 위해 TopicContext를 도입하여 주입하는 구조가 가장 확실하고 리스크가 적습니다.

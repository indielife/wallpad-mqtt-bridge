# 주요 시나리오 시퀀스 다이어그램

> **스레드 구분**
> - **paho thread**: MQTT 콜백(`on_connect`, `on_message`)이 실행되는 paho 내부 스레드
> - **asyncio loop**: `receive_packets()`, `StateSynchronizer.run()` 태스크가 실행되는 이벤트 루프 스레드

---

## 초기화

브릿지는 HA가 discovery를 확인하기 전까지 제어 명령 처리와 RS485 폴링을 차단한다.
`ha_ready`(`asyncio.Event`)가 그 게이트 역할을 한다.

```mermaid
sequenceDiagram
    participant main
    participant Panel
    participant paho as paho thread
    participant aloop as asyncio loop
    participant Broker as MQTT Broker
    participant HA as Home Assistant

    main->>Panel: __init__()
    Note over Panel: _register_topic_routes(), ha_ready 미설정, _loop None
    main->>paho: mqtt.connect()
    main->>aloop: await panel.start()
    aloop->>aloop: await transport.connect()
    aloop->>aloop: create_task(receive_packets())
    aloop->>aloop: create_task(synchronizer.run())
    aloop->>aloop: _loop 할당
    Note over aloop: synchronizer.run() 대기 - await ha_ready.wait()

    paho-->>Panel: on_connect()
    Panel->>Panel: _publish_ha_discovery()
    Note over Panel: ha_ready.clear(), ha_registry 설정
    Panel->>Broker: discovery 토픽 발행 (retain)
    Broker->>HA: discovery 수신

    HA-->>Broker: retained config 에코백
    Broker-->>paho: on_message()
    Note over paho: ha_ready 미설정, topic이 ha_registry와 일치

    paho->>aloop: call_soon_threadsafe(ha_ready.set)
    aloop->>aloop: ha_ready.set()
    Note over aloop: synchronizer.run() 재개 - RS485 폴링 시작
```

---

## HA to Panel (제어 명령)

HA 제어 명령이 내려오면 `device_states`에 목표 상태를 기록하고,
`StateSynchronizer` 다음 순회 시 RS485 패킷을 전송한다.

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant Broker as MQTT Broker
    participant paho as paho thread
    participant Panel
    participant aloop as asyncio loop
    participant RS485 as RS485 Device

    HA->>Broker: 제어 명령 발행
    Note over Broker: homeassistant/light/.../set
    Broker-->>paho: on_message()
    Note over paho: ha_ready 설정됨

    paho->>Panel: parse_message()
    Panel->>Panel: command_registry 조회
    Panel->>Panel: device.resolve_command()
    Panel->>Panel: device_states.update_from_ha()
    Note over Panel: sub_device.set 갱신
    Panel->>Broker: publish_state_to_ha() optimistic
    Broker->>HA: 즉시 상태 반영

    aloop->>aloop: synchronizer.sync_once() 다음 순회
    Note over aloop: reconcile_device() - set != state 감지
    aloop->>aloop: send_packet() - make_packet()
    aloop->>RS485: transport.write_if_idle()
```

---

## Panel to HA (상태 모니터링)

RS485 버스에서 패킷을 수신하면 파싱 후 HA에 상태를 발행한다.

```mermaid
sequenceDiagram
    participant RS485 as RS485 Device
    participant aloop as asyncio loop
    participant Panel
    participant Broker as MQTT Broker
    participant HA as Home Assistant

    RS485->>aloop: 상태 패킷 송신
    Note over aloop: receive_packets() - SOF 감지, 버퍼 누적, 체크섬 검증
    aloop->>Panel: process_packet()
    Panel->>Panel: parser.parse_frame()
    Note over Panel: device, room, value 추출
    Panel->>Panel: set_list()
    Panel->>Panel: device_states.update_from_rs485()
    Panel->>Panel: publish_state_to_ha()
    Panel->>Broker: mqtt_client.publish_json()
    Note over Broker: homeassistant/light/livingroom/state
    Broker->>HA: 상태 수신 - 엔티티 업데이트
```

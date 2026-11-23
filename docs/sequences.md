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
    participant Coordinator as ha_coordinator
    participant paho as paho thread
    participant aloop as asyncio loop
    participant Broker as MQTT Broker
    participant HA as Home Assistant

    main->>Panel: __init__()
    Note over Panel: _register_topic_routes(), ha_coordinator 생성(ha_ready 미설정), _loop None
    main->>paho: mqtt.connect()
    main->>aloop: await panel.start()
    aloop->>aloop: await transport.connect()
    aloop->>aloop: create_task(receive_packets())
    aloop->>aloop: create_task(synchronizer.run())
    aloop->>aloop: _loop 할당
    Note over aloop: synchronizer.run() 대기 - await ha_ready.wait()

    paho-->>Coordinator: on_connect()
    Coordinator->>Coordinator: publish()
    Note over Coordinator: ha_ready.clear(), expected_echo_topic 설정
    Coordinator->>Broker: discovery 토픽 발행 (retain)
    Broker->>HA: discovery 수신

    HA-->>Broker: retained config 에코백
    Broker-->>paho: on_message()
    paho->>Coordinator: handle_echo()
    Note over Coordinator: topic이 expected_echo_topic과 일치

    Coordinator->>aloop: call_soon_threadsafe(ha_ready.set)
    aloop->>aloop: ha_ready.set()
    Note over aloop: synchronizer.run() 재개 - RS485 폴링 시작
```

---

## HA to Panel (제어 명령)

HA 제어 명령이 내려오면 대상 `CategoryController`가 목표 상태를 기록하고,
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

    paho->>aloop: call_soon_threadsafe(명령 처리)
    aloop->>Panel: parse_message()
    Panel->>Panel: command_registry 조회
    Panel->>Panel: device.resolve_command()
    Panel->>Panel: controller_map 조회 - controller.apply_ha_command()
    Note over Panel: sub_device.set 갱신
    Panel->>Broker: publish_state_to_ha() optimistic
    Broker->>HA: 즉시 상태 반영

    aloop->>aloop: synchronizer.sync_once() 다음 순회
    Note over aloop: reconcile_device() - 대기 중인 요청 처리
    aloop->>aloop: send_packet() - make_packet()
    aloop->>RS485: transport.write_if_idle()
```

---

## 난방 명령 확인

난방 명령은 이벤트 루프에서 처리하며 `HeatingCommandTracker`가 방별 현재 요청을 추적한다.
`StateSynchronizer`는 필드별 전송 대신 모드·온도를 포함한 프레임을 한 번 전송한다.

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant Panel
    participant Tracker as HeatingCommandTracker
    participant Sync as StateSynchronizer
    participant Bus as BusArbitrationTransport
    participant Device as 난방 기기

    HA->>Panel: 모드 또는 목표 온도 명령
    Panel->>Tracker: begin(요청값), 새 요청 번호
    Panel->>HA: 낙관적 상태와 확인 대기 진단
    Sync->>Tracker: start_send()
    Sync->>Panel: send_packet(request_id)
    Panel->>Bus: write_if_idle(전체 설정 프레임)
    Bus->>Device: 실제 송신
    Bus-->>Sync: 송신 결과
    Sync->>Tracker: finish_send(요청 번호, 결과)
    Note over Tracker: 실제 송신 완료 시 횟수·대기 시각 갱신
    Device-->>Panel: 상태 프레임
    Panel->>Panel: 길이·종료 바이트·체크섬 검증 및 파싱
    Panel->>Tracker: observe(실제 수신값)
    Tracker->>HA: 상태 일치 시 확인 완료 진단
    Panel->>HA: 실제 수신 상태
    Note over Sync,Tracker: 최초 포함 5회 송신 후에도 미확인이면 경고와 진단 발행
```

HA 디버그 입력은 기기 응답 확인에서 제외한다. 송신 중 도착한 응답은 기록해 두었다가
송신 완료 결과와 함께 판정한다. 관측 기준점은 실제 쓰기 버퍼에 바이트를 넣은 직후
`on_write`로 갱신하고, 재연결 후 각 쓰기에서도 다시 갱신한다.
새 요청이 생기면 이전 송신 결과는 새 요청에 반영하지 않는다.
센서 토픽과 로그 추출 절차는 [난방 진단 가이드](heating_diagnostics.md)를 참조한다.

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
    Panel->>Panel: controller_map 조회 - controller.apply_rs485_state()
    Panel->>Panel: publish_state_to_ha()
    Panel->>Broker: mqtt_client.publish_json()
    Note over Broker: homeassistant/light/livingroom/state
    Broker->>HA: 상태 수신 - 엔티티 업데이트
```

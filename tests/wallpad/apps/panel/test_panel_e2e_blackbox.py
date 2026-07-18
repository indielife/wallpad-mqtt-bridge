"""Panel의 RS485<->MQTT 경계 E2E 블랙박스 특성화 테스트.

원칙:
- 내부 `device_states`/`devices`/`device_map`에 단언하지 않는다. 오직 외부 경계
  (`transport`가 write한 바이트, `MqttClient`가 publish한 페이로드)만 관찰한다.
- 기댓값은 구현 코드가 아니라 Kocom 프로토콜 사양으로부터 독립 유도한다.
  - 상향(RS485->HA): 유효 체크섬을 가진 입력 프레임을 수신 루프에 흘려보내고,
    발행된 상태 토픽/페이로드를 확인한다.
  - 하향(HA->RS485): MQTT 명령 콜백을 전달(deliver)한 뒤, 버스로 나간 바이트를
    파서로 되파싱(round-trip)해 목적지 기기/방/값의 의미가 명령과 일치하는지 본다.

이 테스트는 계층 구조(Room->Controller->SubDevice) 리팩토링 전후로 동일하게
통과해야 하며, 구조가 아니라 외부 계약을 고정한다.
"""

import asyncio
import time

import pytest

# --- 유효 체크섬을 가진 RS485 입력 프레임 (프로토콜 사양으로부터 유도) ---
# 프레임 구조(hex slice): header[0:4]=aa55 type[4:7] order[7:8] pad[8:10]
#   ack:  src_dev[10:12] src_room[12:14] dst_dev[14:16] dst_room[16:18]
#   send: dst_dev[10:12] dst_room[12:14] src_dev[14:16] src_room[16:18]
#   cmd[18:20] value[20:36] checksum[36:38] tail[38:42]
# 기기 hex: light=0e plug=3b thermostat=36 gas=2c elevator=44 fan=48 wallpad=01
# cmd hex: 상태=00 on=01 off=02 / 방 hex: livingroom=00 bedroom=01
LIGHT_LIVING_L1_ON = "aa5530d0000e00010000ff000000000000000e0d0d"
LIGHT_BEDROOM_L1_ON = "aa5530d0000e01010000ff000000000000000f0d0d"
PLUG_LIVING_P1_ON = "aa5530d0003b00010000ff000000000000003b0d0d"
THERMO_LIVING_HEAT_22_CUR_20 = "aa5530d00036000100001100160014000000720d0d"
GAS_ON = "aa5530d0002c0001000100000000000000002e0d0d"
ELEVATOR_ON = "aa5530b00044000100010000000000000000260d0d"
FAN_ON_LOW = "aa5530d000480001000011004000000000009a0d0d"


async def feed_rs485(panel, transport, *packets: str) -> None:
    """유효 프레임 바이트열을 수신 루프에 흘려 전체 파이프를 구동한다.

    마지막에 CancelledError를 넣어 무한 루프를 종료시킨다(수신 태스크 취소 재현).
    """
    seq: list = []
    for packet in packets:
        seq += [bytes.fromhex(packet[i : i + 2]) for i in range(0, len(packet), 2)]
    seq.append(asyncio.CancelledError())
    transport.read.side_effect = seq
    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()


async def drive_reconcile(panel) -> None:
    """HA 명령으로 걸린 set을 버스로 내보내도록 동기화를 1회 구동한다.

    폴링(조회 broadcast)은 이 테스트의 관심사가 아니므로, 모든 방의 스캔 타이머를
    현재 시각으로 맞춰 억제하고 reconcile 경로만 실행한다(하니스 셋업).
    """
    now = time.time()
    for device_state in panel.device_states.values():
        for room_state in device_state.values():
            room_state.scan.tick = now
    await panel.synchronizer.sync_once(now)


def written_hex(transport) -> list[str]:
    """transport.write_if_idle로 나간 바이트를 hex 문자열 리스트로 반환한다."""
    return [bytes(call.args[0]).hex() for call in transport.write_if_idle.await_args_list]


# ============================================================
# 상향 (RS485 -> HA): 수신 프레임이 올바른 상태 토픽/페이로드로 발행되는가
# ============================================================


async def test_upward_light_publishes_room_state(e2e_panel):
    panel, mqtt, transport = e2e_panel
    await feed_rs485(panel, transport, LIGHT_LIVING_L1_ON)

    assert mqtt.json_for("homeassistant/light/livingroom/state") == [
        {"light1": "on", "light2": "off", "light3": "off", "light0": "on"}
    ]


async def test_upward_plug_publishes_room_state(e2e_panel):
    panel, mqtt, transport = e2e_panel
    await feed_rs485(panel, transport, PLUG_LIVING_P1_ON)

    assert mqtt.json_for("homeassistant/switch/livingroom/state") == [
        {"plug1": "on", "plug2": "off", "plug0": "on"}
    ]


async def test_upward_thermostat_publishes_state(e2e_panel):
    panel, mqtt, transport = e2e_panel
    await feed_rs485(panel, transport, THERMO_LIVING_HEAT_22_CUR_20)

    assert mqtt.json_for("homeassistant/climate/livingroom/state") == [
        {"current_temp": 20, "mode": "heat", "target_temp": 22}
    ]


async def test_upward_gas_publishes_sensor_and_switch(e2e_panel):
    panel, mqtt, transport = e2e_panel
    await feed_rs485(panel, transport, GAS_ON)

    assert mqtt.json_for("homeassistant/sensor/wallpad_gas/state") == [{"gas": "on"}]
    assert mqtt.json_for("homeassistant/switch/wallpad_gas/state") == [{"gas": "on"}]


async def test_upward_elevator_publishes_state(e2e_panel):
    panel, mqtt, transport = e2e_panel
    await feed_rs485(panel, transport, ELEVATOR_ON)

    assert mqtt.json_for("homeassistant/switch/wallpad/state") == [{"elevator": "off"}]


async def test_upward_fan_publishes_state(e2e_panel):
    panel, mqtt, transport = e2e_panel
    await feed_rs485(panel, transport, FAN_ON_LOW)

    assert mqtt.json_for("homeassistant/fan/wallpad/state") == [{"mode": "on", "speed": "low"}]


# ============================================================
# 하향 (HA -> RS485): MQTT 명령이 올바르게 주소지정된 패킷으로 버스에 나가는가
# ============================================================


async def test_downward_light_writes_addressed_packet(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/light/livingroom_light1/set", "on")
    await drive_reconcile(panel)

    writes = written_hex(transport)
    assert len(writes) == 1
    frame = panel.parser.parse_frame(writes[0], panel.device_states)
    assert frame["dst_device"] == "light"
    assert frame["dst_room"] == "livingroom"
    assert frame["value"] == "ff00000000000000"  # slot1 on, 나머지 off
    assert panel.parser.validate_checksum(writes[0])[0] is True


async def test_downward_plug_writes_addressed_packet(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/switch/livingroom_plug1/set", "on")
    await drive_reconcile(panel)

    writes = written_hex(transport)
    assert len(writes) == 1
    frame = panel.parser.parse_frame(writes[0], panel.device_states)
    assert frame["dst_device"] == "plug"
    assert frame["dst_room"] == "livingroom"
    # 콘센트 기본 상태는 on이라, plug1 명령 시 이미 켜져 있는 plug2도 함께 실린다.
    assert frame["value"] == "ffff000000000000"
    assert panel.parser.validate_checksum(writes[0])[0] is True


async def test_downward_thermostat_writes_heat_setpoint(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    await drive_reconcile(panel)

    writes = written_hex(transport)
    assert writes, "보일러 목표온도 명령이 버스로 나가야 한다"
    for hexpk in writes:
        frame = panel.parser.parse_frame(hexpk, panel.device_states)
        assert frame["dst_device"] == "thermostat"
        assert frame["dst_room"] == "livingroom"
        assert frame["value"][:2] == "11"  # heat 모드
        assert frame["value"][4:6] == "19"  # 목표 25도(0x19)
        assert panel.parser.validate_checksum(hexpk)[0] is True


async def test_downward_thermostat_optimistic_echo(e2e_panel):
    _panel, mqtt, _transport = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")

    # 낙관적 반영: 명령 즉시 HA로 상태 에코 (reconcile 이전)
    assert mqtt.json_for("homeassistant/climate/livingroom/state") == [
        {"mode": "heat", "target_temp": 25, "current_temp": 0}
    ]


async def test_downward_elevator_off_optimistic_echo(e2e_panel):
    _panel, mqtt, _transport = e2e_panel
    mqtt.deliver("homeassistant/switch/wallpad_elevator/set", "off")

    assert mqtt.json_for("homeassistant/switch/wallpad/state") == [{"elevator": "off"}]


async def test_downward_gas_on_command_is_blocked(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/switch/wallpad_gas/set", "on")
    await drive_reconcile(panel)

    # 가스 밸브 원격 개방(on)은 금지되어야 하며 버스로 어떤 패킷도 나가면 안 된다.
    assert written_hex(transport) == []


# ============================================================
# 다중 방 라우팅 격리
# ============================================================


async def test_multiroom_upward_does_not_cross_publish(e2e_panel_multiroom):
    panel, mqtt, transport = e2e_panel_multiroom
    await feed_rs485(panel, transport, LIGHT_LIVING_L1_ON)

    topics = mqtt.json_topics()
    assert "homeassistant/light/livingroom/state" in topics
    assert all("bedroom" not in topic for topic in topics)


async def test_multiroom_downward_addresses_only_target_room(e2e_panel_multiroom):
    panel, mqtt, transport = e2e_panel_multiroom
    mqtt.deliver("homeassistant/light/bedroom_light1/set", "on")
    await drive_reconcile(panel)

    writes = written_hex(transport)
    assert len(writes) == 1
    frame = panel.parser.parse_frame(writes[0], panel.device_states)
    assert frame["dst_device"] == "light"
    assert frame["dst_room"] == "bedroom"


async def test_multiroom_upward_bedroom_publishes_own_room(e2e_panel_multiroom):
    panel, mqtt, transport = e2e_panel_multiroom
    await feed_rs485(panel, transport, LIGHT_BEDROOM_L1_ON)

    assert mqtt.json_for("homeassistant/light/bedroom/state") == [
        {"light1": "on", "light2": "off", "light0": "on"}
    ]
    assert "homeassistant/light/livingroom/state" not in mqtt.json_topics()

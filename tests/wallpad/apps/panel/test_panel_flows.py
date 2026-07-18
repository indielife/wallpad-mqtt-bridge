"""HA 명령/RS485 수신이 상태 소유자(CategoryController)의 RoomState에 반영되는지 검증.

상태 소유권이 컨트롤러로 이전된 뒤에는, 내부 device_states dict를 직접 인덱싱하는
대신 상태를 소유한 컨트롤러(`controller_map`)를 통해 단언한다.
"""

from wallpad.apps.panel.panel import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
)


def state_of(panel, device, room):
    """(device, room) 카테고리 컨트롤러가 소유한 RoomState를 반환한다."""
    return panel.controller_map[(device, room)].state


def test_parse_message_light_plug(panel_instance):
    """MQTT 조명 및 콘센트 제어 메시지가 소유 컨트롤러 상태에 반영되는지 검증합니다."""
    # 조명 1 켜기 명령어 처리
    topic_light = ["homeassistant", "light", "livingroom_light1", "set"]
    panel_instance.parse_message(topic_light, "on")
    light = state_of(panel_instance, DEVICE_LIGHT, "livingroom")
    assert light["light1"].set == "on"
    assert light["light1"].last == "set"

    # 콘센트 2 끄기 명령어 처리
    topic_plug = ["homeassistant", "switch", "livingroom_plug2", "set"]
    panel_instance.parse_message(topic_plug, "off")
    plug = state_of(panel_instance, DEVICE_PLUG, "livingroom")
    assert plug["plug2"].set == "off"
    assert plug["plug2"].last == "set"


def test_parse_message_gas_and_elevator(panel_instance):
    """MQTT 가스밸브 및 엘리베이터 제어 메시지 처리 흐름을 검증합니다."""
    # 가스밸브 'on' 명령어 차단 여부 검증
    topic_gas = ["homeassistant", "switch", "wallpad_gas", "set"]
    panel_instance.parse_message(topic_gas, "on")
    gas = state_of(panel_instance, DEVICE_GAS, "wallpad")
    assert gas["gas"].set == "off"  # "on"은 허용되지 않음

    # 가스밸브 'off' 명령어는 허용
    panel_instance.parse_message(topic_gas, "off")
    assert gas["gas"].set == "off"
    assert gas["gas"].last == "set"

    # 엘리베이터 'on' 명령어 처리 검증
    topic_elevator = ["homeassistant", "switch", "wallpad_elevator", "set"]
    panel_instance.parse_message(topic_elevator, "on")
    elevator = state_of(panel_instance, DEVICE_ELEVATOR, "wallpad")
    assert elevator["elevator"].set == "on"
    assert elevator["elevator"].last == "set"


def test_parse_message_thermostat(panel_instance):
    """MQTT 보일러 목표 온도 및 모드 제어 메시지가 소유 컨트롤러 상태에 반영되는지 검증합니다."""
    # 보일러 온도 25도로 변경 시 모드는 자동으로 heat으로 작동
    topic_temp = ["homeassistant", "climate", "livingroom", "target_temp"]
    panel_instance.parse_message(topic_temp, "25.0")
    thermo = state_of(panel_instance, DEVICE_THERMOSTAT, "livingroom")
    assert thermo["target_temp"].set == 25
    assert thermo["mode"].set == "heat"
    assert thermo["target_temp"].last == "set"
    assert thermo["mode"].last == "set"

    # 보일러 모드 끄기 명령어 처리
    topic_mode = ["homeassistant", "climate", "livingroom", "mode"]
    panel_instance.parse_message(topic_mode, "off")
    assert thermo["mode"].set == "off"
    assert thermo["mode"].last == "set"


def test_parse_message_fan(panel_instance):
    """MQTT 환기팬 제어 메시지가 소유 컨트롤러 상태에 반영되는지 검증합니다."""
    # 환기팬 모드 on 변경 시 기본 속도는 default_speed (low)으로 작동
    topic_mode = ["homeassistant", "fan", "wallpad", "mode"]
    panel_instance.parse_message(topic_mode, "on")
    fan = state_of(panel_instance, DEVICE_FAN, "wallpad")
    assert fan["mode"].set == "on"
    assert fan["speed"].set == "low"
    assert fan["mode"].last == "set"
    assert fan["speed"].last == "set"

    # 스피드를 직접 high로 변경
    topic_speed = ["homeassistant", "fan", "wallpad", "speed"]
    panel_instance.parse_message(topic_speed, "high")
    assert fan["speed"].set == "high"
    assert fan["mode"].set == "on"


def test_process_packet_light_status(panel_instance):
    """RS485 조명 상태 수신 패킷이 소유 컨트롤러 상태를 갱신하고 스캔을 초기화하는지 검증합니다."""
    # 거실(livingroom) 조명 상태 수신 ACK 패킷 (light1 켜짐, light2 & light3 꺼짐)
    # aa55(header) 30d(type:ack) 0(order) 00(pad) 0e(light) 00(livingroom) 0100(dst:wallpad) 00(상태) ff00000000000000(value) 00(checksum) 0d0d(tail)
    packet = "aa5530d0000e00010000ff00000000000000000d0d"
    panel_instance.process_packet(packet)

    light = state_of(panel_instance, DEVICE_LIGHT, "livingroom")
    assert light["light1"].state == "on"
    assert light["light2"].state == "off"
    assert light["light3"].state == "off"
    assert light.scan.tick > 0.0


def test_process_packet_thermostat_status(panel_instance):
    """RS485 보일러 상태 수신 패킷이 소유 컨트롤러 상태를 갱신하고 스캔을 초기화하는지 검증합니다."""
    # 거실(livingroom) 보일러 상태 수신 ACK 패킷 (heat모드, 목표 22도, 현재 20도)
    # aa55 30d 0 00 36(thermo) 00(livingroom) 0100(dst:wallpad) 00(상태) 1100160014000000(value) 00 0d0d
    packet = "aa5530d00036000100001100160014000000000d0d"
    panel_instance.process_packet(packet)

    thermo = state_of(panel_instance, DEVICE_THERMOSTAT, "livingroom")
    assert thermo["mode"].state == "heat"
    assert thermo["target_temp"].state == 22
    assert thermo["current_temp"].state == 20
    assert thermo.scan.tick > 0.0

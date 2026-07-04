import json

import pytest

from wallpad.ventilator.devices.grex import HA_FAN, HA_PREFIX, HA_SENSOR, GrexVentilator


@pytest.fixture
def grex_device():
    """테스트에 사용할 GrexVentilator 인스턴스를 제공하는 픽스처입니다."""
    return GrexVentilator(name_prefix="test_grex", sw_version="1.0.0")


def test_grex_init(grex_device):
    """GrexVentilator 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert grex_device.name_prefix == "test_grex"
    assert grex_device.sw_version == "1.0.0"
    assert grex_device.room == "grex"
    assert grex_device.sub_device == "fan"


def test_grex_get_discovery_payloads_add(grex_device):
    """디스커버리 추가(remove=False) 시 정상적인 토픽과 JSON 페이로드를 반환하는지 검증합니다."""
    payloads = grex_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 3
    fan_topic, fan_payload_str = payloads[0]
    mode_topic, mode_payload_str = payloads[1]
    speed_topic, speed_payload_str = payloads[2]

    assert fan_topic == f"{HA_PREFIX}/{HA_FAN}/grex_fan/config"
    assert mode_topic == f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_mode/config"
    assert speed_topic == f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_speed/config"

    expected_device_info = {
        "name": "Grex Ventilator",
        "identifiers": "grex_ventilator",
        "manufacturer": "Grex",
        "model": "Ventilator",
        "sw_version": "1.0.0",
    }

    expected_fan_payload = {
        "name": "test_grex_fan",
        "command_topic": f"{HA_PREFIX}/{HA_FAN}/grex/mode",
        "state_topic": f"{HA_PREFIX}/{HA_FAN}/grex/state",
        "spd_cmd_t": f"{HA_PREFIX}/{HA_FAN}/grex/speed",
        "spd_stat_t": f"{HA_PREFIX}/{HA_FAN}/grex/state",
        "state_value_template": "{{ value_json.mode }}",
        "spd_val_tpl": "{{ value_json.speed }}",
        "payload_on": "on",
        "payload_off": "off",
        "spds": ["low", "medium", "high", "off"],
        "unique_id": "test_grex_grex_fan",
        "device": expected_device_info,
    }

    expected_mode_payload = {
        "name": "test_grex_fan_mode",
        "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/grex_fan/state",
        "value_template": "{{ value_json.fan_mode }}",
        "icon": "mdi:play-circle-outline",
        "unique_id": "test_grex_grex_fan_mode",
        "device": expected_device_info,
    }

    expected_speed_payload = {
        "name": "test_grex_fan_speed",
        "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/grex_fan/state",
        "value_template": "{{ value_json.fan_speed }}",
        "icon": "mdi:speedometer",
        "unique_id": "test_grex_grex_fan_speed",
        "device": expected_device_info,
    }

    assert json.loads(fan_payload_str) == expected_fan_payload
    assert json.loads(mode_payload_str) == expected_mode_payload
    assert json.loads(speed_payload_str) == expected_speed_payload


def test_grex_get_discovery_payloads_remove(grex_device):
    """디스커버리 삭제(remove=True) 시 빈 문자열 페이로드를 반환하는지 검증합니다."""
    payloads = grex_device.get_discovery_payloads(remove=True)
    assert payloads[0] == (f"{HA_PREFIX}/{HA_FAN}/grex_fan/config", "")
    assert payloads[1] == (f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_mode/config", "")
    assert payloads[2] == (f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_speed/config", "")


def test_grex_get_subscribe_topics(grex_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = grex_device.get_subscribe_topics()
    assert topics == [
        f"{HA_PREFIX}/{HA_FAN}/grex_fan/config",
        f"{HA_PREFIX}/{HA_FAN}/grex/mode",
        f"{HA_PREFIX}/{HA_FAN}/grex/speed",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_mode/config",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_speed/config",
    ]


def test_grex_state_topics_match_discovery(grex_device):
    """state 발행 토픽이 discovery에 선언된 state_topic과 일치하는지 검증합니다."""
    assert grex_device.fan_state_topic == f"{HA_PREFIX}/{HA_FAN}/grex/state"
    assert grex_device.sensor_state_topic == f"{HA_PREFIX}/{HA_SENSOR}/grex_fan/state"


# ---------------------------------------------------------------------------
# build_sensor_payload 매핑 테스트
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "ha_mode_on", "expected_fan_mode"),
    [
        ("auto", False, "자동"),
        ("manual", False, "수동"),
        ("sleep", False, "취침"),
        ("off", True, "HA"),
        ("off", False, "off"),
    ],
)
def test_build_sensor_payload_fan_mode_mapping(grex_device, mode, ha_mode_on, expected_fan_mode):
    """mode(+ ha_mode_on 플래그)가 한글 fan_mode로 매핑된다."""
    payload = grex_device.build_sensor_payload(mode, "off", ha_mode_on=ha_mode_on)
    assert payload["fan_mode"] == expected_fan_mode


@pytest.mark.parametrize(
    ("speed", "expected_fan_speed"),
    [
        ("low", "1단"),
        ("medium", "2단"),
        ("high", "3단"),
        ("off", "대기"),
    ],
)
def test_build_sensor_payload_fan_speed_mapping(grex_device, speed, expected_fan_speed):
    """speed가 한글 fan_speed로 매핑된다 (mode는 항상 통과되는 상태로 고정)."""
    payload = grex_device.build_sensor_payload("manual", speed, ha_mode_on=False)
    assert payload["fan_speed"] == expected_fan_speed


def test_build_sensor_payload_guard_blocks_when_off_and_ha_off(grex_device):
    """mode가 off이고 ha_mode_on도 False이면 가드에 걸려 off/off 그대로 반환한다."""
    payload = grex_device.build_sensor_payload("off", "low", ha_mode_on=False)
    assert payload == {"fan_mode": "off", "fan_speed": "off"}

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

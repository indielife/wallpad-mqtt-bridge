import json

import pytest

from wallpad.mqtt import HA_CLIMATE, HA_PREFIX
from wallpad.panel.devices.thermostat import Thermostat
from wallpad.panel.topic import TopicBuilder


@pytest.fixture
def thermostat_device():
    """테스트에 사용할 Thermostat 인스턴스를 제공하는 픽스처입니다."""
    topics = TopicBuilder.for_thermostat(room="room1")
    return Thermostat(name_prefix="test_kocom", room="room1", sw_version="1.0.0", topics=topics)


def test_thermostat_init(thermostat_device):
    """Thermostat 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert thermostat_device.name_prefix == "test_kocom"
    assert thermostat_device.sw_version == "1.0.0"
    assert thermostat_device.room == "room1"
    assert thermostat_device.sub_device == "thermostat"


def test_thermostat_get_discovery_payloads_add(thermostat_device):
    """디스커버리 추가(remove=False) 시 정상적인 토픽과 JSON 페이로드를 반환하는지 검증합니다."""
    payloads = thermostat_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 1
    topic, payload_str = payloads[0]

    assert topic == f"{HA_PREFIX}/{HA_CLIMATE}/room1/config"

    expected_payload = {
        "name": "test_kocom_room1_thermostat",
        "mode_command_topic": f"{HA_PREFIX}/{HA_CLIMATE}/room1/mode",
        "mode_state_topic": f"{HA_PREFIX}/{HA_CLIMATE}/room1/state",
        "mode_state_template": "{{ value_json.mode }}",
        "temperature_command_topic": f"{HA_PREFIX}/{HA_CLIMATE}/room1/target_temp",
        "temperature_state_topic": f"{HA_PREFIX}/{HA_CLIMATE}/room1/state",
        "temperature_state_template": "{{ value_json.target_temp }}",
        "current_temperature_topic": f"{HA_PREFIX}/{HA_CLIMATE}/room1/state",
        "current_temperature_template": "{{ value_json.current_temp }}",
        "min_temp": 5,
        "max_temp": 40,
        "temp_step": 1,
        "modes": ["off", "heat", "fan_only"],
        "unique_id": "test_kocom_room1_thermostat",
        "device": thermostat_device.device_info,
    }
    assert json.loads(payload_str) == expected_payload


def test_thermostat_get_discovery_payloads_remove(thermostat_device):
    """디스커버리 삭제(remove=True) 시 빈 문자열 페이로드를 반환하는지 검증합니다."""
    payloads = thermostat_device.get_discovery_payloads(remove=True)
    assert len(payloads) == 1
    assert payloads[0] == (f"{HA_PREFIX}/{HA_CLIMATE}/room1/config", "")


def test_thermostat_get_ha_state_messages(thermostat_device):
    """room 단위 state 토픽과 value를 그대로 반환하는지 검증합니다."""
    value = {"mode": "heat", "target_temp": 22, "current_temp": 20}
    messages = thermostat_device.get_ha_state_messages(value)
    assert messages == [(f"{HA_PREFIX}/{HA_CLIMATE}/room1/state", value)]


def test_thermostat_get_subscribe_topics(thermostat_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = thermostat_device.get_subscribe_topics()
    assert topics == [
        f"{HA_PREFIX}/{HA_CLIMATE}/room1/config",
        f"{HA_PREFIX}/{HA_CLIMATE}/room1/mode",
        f"{HA_PREFIX}/{HA_CLIMATE}/room1/target_temp",
    ]

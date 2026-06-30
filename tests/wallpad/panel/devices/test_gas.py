import json

import pytest

from wallpad.mqtt import HA_PREFIX, HA_SENSOR, HA_SWITCH
from wallpad.panel.devices.gas import Gas
from wallpad.panel.topic import TopicBuilder


@pytest.fixture
def gas_device():
    """테스트에 사용할 Gas 인스턴스를 제공하는 픽스처입니다."""
    topics = TopicBuilder.for_gas(room="wallpad", sub_device="gas")
    return Gas(name_prefix="test_kocom", sw_version="1.0.0", topics=topics)


def test_gas_init(gas_device):
    """Gas 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert gas_device.name_prefix == "test_kocom"
    assert gas_device.sw_version == "1.0.0"
    assert gas_device.room == "wallpad"
    assert gas_device.sub_device == "gas"


def test_gas_get_discovery_payloads_add(gas_device):
    """디스커버리 추가(remove=False) 시 스위치와 센서의 페이로드를 반환하는지 검증합니다."""
    payloads = gas_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 2
    switch_topic, switch_payload_str = payloads[0]
    sensor_topic, sensor_payload_str = payloads[1]

    assert switch_topic == f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/config"
    assert sensor_topic == f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/config"

    expected_switch_payload = {
        "name": "test_kocom_wallpad_gas",
        "command_topic": f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/set",
        "state_topic": f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/state",
        "value_template": "{{ value_json.gas }}",
        "icon": "mdi:gas-cylinder",
        "payload_on": "on",
        "payload_off": "off",
        "unique_id": "test_kocom_wallpad_gas",
        "device": {
            "name": "Kocom wallpad",
            "identifiers": "kocom_wallpad",
            "manufacturer": "KOCOM",
            "model": "Wallpad",
            "sw_version": "1.0.0",
        },
    }

    expected_sensor_payload = {
        "name": "test_kocom_wallpad_gas",
        "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/state",
        "value_template": "{{ value_json.gas }}",
        "icon": "mdi:gas-cylinder",
        "unique_id": "test_kocom_wallpad_gas",
        "device": {
            "name": "Kocom wallpad",
            "identifiers": "kocom_wallpad",
            "manufacturer": "KOCOM",
            "model": "Wallpad",
            "sw_version": "1.0.0",
        },
    }

    assert json.loads(switch_payload_str) == expected_switch_payload
    assert json.loads(sensor_payload_str) == expected_sensor_payload


def test_gas_get_discovery_payloads_remove(gas_device):
    """디스커버리 삭제(remove=True) 시 빈 문자열 페이로드를 반환하는지 검증합니다."""
    payloads = gas_device.get_discovery_payloads(remove=True)

    assert len(payloads) == 2
    assert payloads[0] == (f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/config", "")
    assert payloads[1] == (f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/config", "")


def test_gas_get_ha_state_messages(gas_device):
    """sensor와 switch 두 토픽 모두에 {sub_device: value} 형태로 반환하는지 검증합니다."""
    messages = gas_device.get_ha_state_messages("off")
    assert messages == [
        (f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/state", {"gas": "off"}),
        (f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/state", {"gas": "off"}),
    ]


def test_gas_get_subscribe_topics(gas_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = gas_device.get_subscribe_topics()

    assert topics == [
        f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/config",
        f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/config",
        f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/set",
    ]

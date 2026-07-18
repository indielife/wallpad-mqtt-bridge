import json

import pytest

from wallpad.apps.panel.devices.light import Light
from wallpad.apps.panel.topic import TopicBuilder
from wallpad.mqtt import HA_LIGHT, HA_PREFIX
from wallpad.protocol.kocom import constants as kocom_const


@pytest.fixture
def light_device():
    """테스트에 사용할 Light 인스턴스를 제공하는 픽스처입니다."""
    topics = TopicBuilder.for_light(room="room1", sub_device="light1")
    return Light(
        name_prefix="test_kocom",
        room="room1",
        sub_device="light1",
        sw_version="1.0.0",
        hw_info=kocom_const.HARDWARE,
        topics=topics,
    )


def test_light_init(light_device):
    """Light 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert light_device.name_prefix == "test_kocom"
    assert light_device.sw_version == "1.0.0"
    assert light_device.room == "room1"
    assert light_device.sub_device == "light1"


def test_light_get_discovery_payloads_add(light_device):
    """디스커버리 추가(remove=False) 시 정상적인 토픽과 JSON 페이로드를 반환하는지 검증합니다."""
    payloads = light_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 1
    topic, payload_str = payloads[0]

    assert topic == f"{HA_PREFIX}/{HA_LIGHT}/room1_light1/config"

    expected_payload = {
        "name": "test_kocom_room1_light1",
        "command_topic": f"{HA_PREFIX}/{HA_LIGHT}/room1_light1/set",
        "state_topic": f"{HA_PREFIX}/{HA_LIGHT}/room1/state",
        "value_template": "{{ value_json.light1 }}",
        "payload_on": "on",
        "payload_off": "off",
        "unique_id": "test_kocom_room1_light1",
        "device": light_device.device_info,
    }
    assert json.loads(payload_str) == expected_payload


def test_light_get_ha_state_messages(light_device):
    """room 단위 state 토픽과 value를 그대로 반환하는지 검증합니다."""
    value = {"light1": "on", "light2": "off"}
    messages = light_device.get_ha_state_messages(value)
    assert messages == [(f"{HA_PREFIX}/{HA_LIGHT}/room1/state", value)]


def test_light_get_subscribe_topics(light_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = light_device.get_subscribe_topics()
    assert topics == [
        f"{HA_PREFIX}/{HA_LIGHT}/room1_light1/config",
        f"{HA_PREFIX}/{HA_LIGHT}/room1_light1/set",
    ]

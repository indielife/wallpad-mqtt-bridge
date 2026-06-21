import json

import pytest

from wallpad.panel.devices.elevator import HA_PREFIX, HA_SWITCH, Elevator


@pytest.fixture
def elevator_device():
    """테스트에 사용할 Elevator 인스턴스를 제공하는 픽스처입니다."""
    return Elevator(name_prefix="test_kocom", sw_version="1.0.0")


def test_elevator_init(elevator_device):
    """Elevator 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert elevator_device.name_prefix == "test_kocom"
    assert elevator_device.sw_version == "1.0.0"
    assert elevator_device.room == "wallpad"
    assert elevator_device.sub_device == "elevator"


def test_elevator_get_discovery_payloads_add(elevator_device):
    """디스커버리 추가(remove=False) 시 정상적인 토픽과 JSON 페이로드를 반환하는지 검증합니다."""
    payloads = elevator_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 1
    topic, payload_str = payloads[0]

    assert topic == f"{HA_PREFIX}/{HA_SWITCH}/wallpad_elevator/config"

    expected_payload = {
        "name": "test_kocom_wallpad_elevator",
        "command_topic": f"{HA_PREFIX}/{HA_SWITCH}/wallpad_elevator/set",
        "state_topic": f"{HA_PREFIX}/{HA_SWITCH}/wallpad/state",
        "value_template": "{{ value_json.elevator }}",
        "icon": "mdi:elevator",
        "payload_on": "on",
        "payload_off": "off",
        "unique_id": "test_kocom_wallpad_elevator",
        "device": {
            "name": "Kocom wallpad",
            "ids": "kocom_wallpad",
            "mf": "KOCOM",
            "mdl": "Wallpad",
            "sw": "1.0.0",
        },
    }
    assert json.loads(payload_str) == expected_payload


def test_elevator_get_discovery_payloads_remove(elevator_device):
    """디스커버리 삭제(remove=True) 시 빈 문자열 페이로드를 반환하는지 검증합니다."""
    payloads = elevator_device.get_discovery_payloads(remove=True)

    assert len(payloads) == 1
    topic, payload_str = payloads[0]

    assert topic == f"{HA_PREFIX}/{HA_SWITCH}/wallpad_elevator/config"
    assert payload_str == ""  # 삭제를 위해 페이로드는 비어 있어야 함


def test_elevator_get_ha_state_messages(elevator_device):
    """state 토픽에 {sub_device: value} 형태로 래핑하여 반환하는지 검증합니다."""
    messages = elevator_device.get_ha_state_messages("on")
    assert messages == [(f"{HA_PREFIX}/{HA_SWITCH}/wallpad/state", {"elevator": "on"})]


def test_elevator_get_subscribe_topics(elevator_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = elevator_device.get_subscribe_topics()

    assert topics == [
        f"{HA_PREFIX}/{HA_SWITCH}/wallpad_elevator/config",
        f"{HA_PREFIX}/{HA_SWITCH}/wallpad_elevator/set",
    ]

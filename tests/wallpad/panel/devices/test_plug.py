import json

import pytest

from wallpad.panel.devices.plug import HA_PREFIX, HA_SWITCH, Plug


@pytest.fixture
def plug_device():
    """테스트에 사용할 Plug 인스턴스를 제공하는 픽스처입니다."""
    return Plug(name_prefix="test_kocom", room="room1", sub_device="plug1", sw_version="1.0.0")


def test_plug_init(plug_device):
    """Plug 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert plug_device.name_prefix == "test_kocom"
    assert plug_device.sw_version == "1.0.0"
    assert plug_device.room == "room1"
    assert plug_device.sub_device == "plug1"


def test_plug_get_discovery_payloads_add(plug_device):
    """디스커버리 추가(remove=False) 시 정상적인 토픽과 JSON 페이로드를 반환하는지 검증합니다."""
    payloads = plug_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 1
    topic, payload_str = payloads[0]

    assert topic == f"{HA_PREFIX}/{HA_SWITCH}/room1_plug1/config"

    expected_payload = {
        "name": "test_kocom_room1_plug1",
        "cmd_t": f"{HA_PREFIX}/{HA_SWITCH}/room1_plug1/set",
        "stat_t": f"{HA_PREFIX}/{HA_SWITCH}/room1/state",
        "val_tpl": "{{ value_json.plug1 }}",
        "ic": "mdi:power-socket-eu",
        "pl_on": "on",
        "pl_off": "off",
        "uniq_id": "test_kocom_room1_plug1",
        "device": plug_device.device_info,
    }
    assert json.loads(payload_str) == expected_payload


def test_plug_get_ha_state_messages(plug_device):
    """room 단위 state 토픽과 value를 그대로 반환하는지 검증합니다."""
    value = {"plug1": "on", "plug2": "off"}
    messages = plug_device.get_ha_state_messages(value)
    assert messages == [(f"{HA_PREFIX}/{HA_SWITCH}/room1/state", value)]


def test_plug_get_subscribe_topics(plug_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = plug_device.get_subscribe_topics()
    assert topics == [
        f"{HA_PREFIX}/{HA_SWITCH}/room1_plug1/config",
        f"{HA_PREFIX}/{HA_SWITCH}/room1_plug1/set",
    ]

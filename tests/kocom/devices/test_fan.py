import json

import pytest

from kocom.devices.fan import HA_FAN, HA_PREFIX, Fan


@pytest.fixture
def fan_device():
    """테스트에 사용할 Fan 인스턴스를 제공하는 픽스처입니다."""
    return Fan(name_prefix="test_kocom", sw_version="1.0.0")


def test_fan_init(fan_device):
    """Fan 인스턴스 초기화 시 방 이름과 sub_device가 올바르게 설정되는지 검증합니다."""
    assert fan_device.name_prefix == "test_kocom"
    assert fan_device.sw_version == "1.0.0"
    assert fan_device.room == "wallpad"
    assert fan_device.sub_device == "fan"


def test_fan_get_discovery_payloads_add(fan_device):
    """디스커버리 추가(remove=False) 시 정상적인 토픽과 JSON 페이로드를 반환하는지 검증합니다."""
    payloads = fan_device.get_discovery_payloads(remove=False)

    assert len(payloads) == 1
    topic, payload_str = payloads[0]

    assert topic == f"{HA_PREFIX}/{HA_FAN}/wallpad_fan/config"

    expected_payload = {
        "name": "test_kocom_wallpad_fan",
        "cmd_t": f"{HA_PREFIX}/{HA_FAN}/wallpad/mode",
        "stat_t": f"{HA_PREFIX}/{HA_FAN}/wallpad/state",
        "spd_cmd_t": f"{HA_PREFIX}/{HA_FAN}/wallpad/speed",
        "spd_stat_t": f"{HA_PREFIX}/{HA_FAN}/wallpad/state",
        "stat_val_tpl": "{{ value_json.mode }}",
        "spd_val_tpl": "{{ value_json.speed }}",
        "pl_on": "on",
        "pl_off": "off",
        "spds": ["low", "medium", "high", "off"],
        "uniq_id": "test_kocom_wallpad_fan",
        "device": fan_device.device_info,
    }
    assert json.loads(payload_str) == expected_payload


def test_fan_get_discovery_payloads_remove(fan_device):
    """디스커버리 삭제(remove=True) 시 빈 문자열 페이로드를 반환하는지 검증합니다."""
    payloads = fan_device.get_discovery_payloads(remove=True)
    assert payloads[0] == (f"{HA_PREFIX}/{HA_FAN}/wallpad_fan/config", "")


def test_fan_get_subscribe_topics(fan_device):
    """구독해야 할 토픽 리스트가 정상적으로 반환되는지 검증합니다."""
    topics = fan_device.get_subscribe_topics()
    assert topics == [
        f"{HA_PREFIX}/{HA_FAN}/wallpad_fan/config",
        f"{HA_PREFIX}/{HA_FAN}/wallpad/mode",
        f"{HA_PREFIX}/{HA_FAN}/wallpad/speed",
    ]

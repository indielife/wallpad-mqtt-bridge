import json

import pytest

from wallpad.mqtt import HA_FAN, HA_PREFIX, HA_SENSOR
from wallpad.protocol.grex import constants as grex_const
from wallpad.ventilator.devices import (
    VentilatorController,
    VentilatorUnit,
)

EXPECTED_DEVICE_INFO = {
    "identifiers": "grex_ventilator",
    "name": "grex Ventilator",
    "manufacturer": "GREX",
    "model": "Ventilator",
    "sw_version": "1.0.0",
}


@pytest.fixture
def unit():
    """HA fan 도메인을 담당하는 환기장치 본체 픽스처입니다."""
    return VentilatorUnit(
        name_prefix="test_grex",
        sw_version="1.0.0",
        hw_info=grex_const.HARDWARE,
    )


@pytest.fixture
def controller():
    """HA sensor 도메인(모드/속도 표시)을 담당하는 조작기 픽스처입니다."""
    return VentilatorController(
        name_prefix="test_grex",
        sw_version="1.0.0",
        hw_info=grex_const.HARDWARE,
    )


# ---------------------------------------------------------------------------
# 공통 초기화
# ---------------------------------------------------------------------------


def test_grex_devices_share_identity(unit, controller):
    """Unit/Controller가 동일한 room·sub_device·device_info를 공유하는지 검증합니다."""
    for device in (unit, controller):
        assert device.name_prefix == "test_grex"
        assert device.room == "grex"
        assert device.sub_device == "fan"
        assert device.device_info == EXPECTED_DEVICE_INFO


# ---------------------------------------------------------------------------
# Unit (HA fan)
# ---------------------------------------------------------------------------


def test_unit_state_topic(unit):
    assert unit.state_topic == f"{HA_PREFIX}/{HA_FAN}/grex/state"


def test_unit_discovery_payloads_add(unit):
    """본체 discovery가 fan config 1건과 state_topic 일치를 반환하는지 검증합니다."""
    payloads = unit.get_discovery_payloads(remove=False)

    assert len(payloads) == 1
    fan_topic, fan_payload_str = payloads[0]
    assert fan_topic == f"{HA_PREFIX}/{HA_FAN}/grex_fan/config"

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
        "device": EXPECTED_DEVICE_INFO,
    }
    assert json.loads(fan_payload_str) == expected_fan_payload


def test_unit_discovery_payloads_remove(unit):
    payloads = unit.get_discovery_payloads(remove=True)
    assert payloads == [(f"{HA_PREFIX}/{HA_FAN}/grex_fan/config", "")]


def test_unit_get_subscribe_topics(unit):
    assert unit.get_subscribe_topics() == [
        f"{HA_PREFIX}/{HA_FAN}/grex_fan/config",
        f"{HA_PREFIX}/{HA_FAN}/grex/mode",
        f"{HA_PREFIX}/{HA_FAN}/grex/speed",
    ]


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        (f"{HA_PREFIX}/{HA_FAN}/grex/mode", "mode"),
        (f"{HA_PREFIX}/{HA_FAN}/grex/speed", "speed"),
        (f"{HA_PREFIX}/{HA_FAN}/grex_fan/config", None),
        (f"{HA_PREFIX}/{HA_FAN}/grex/state", None),
    ],
)
def test_unit_resolve_command_key(unit, topic, expected):
    """구독 토픽이 fan 명령 키로 변환되고, config echo 등은 None이 된다."""
    assert unit.resolve_command_key(topic) == expected


# ---------------------------------------------------------------------------
# Controller (HA sensor)
# ---------------------------------------------------------------------------


def test_controller_state_topic(controller):
    assert controller.state_topic == f"{HA_PREFIX}/{HA_SENSOR}/grex_fan/state"


def test_controller_discovery_payloads_add(controller):
    """조작기 discovery가 mode/speed sensor config 2건을 반환하는지 검증합니다."""
    payloads = controller.get_discovery_payloads(remove=False)

    assert len(payloads) == 2
    mode_topic, mode_payload_str = payloads[0]
    speed_topic, speed_payload_str = payloads[1]

    assert mode_topic == f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_mode/config"
    assert speed_topic == f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_speed/config"

    expected_mode_payload = {
        "name": "test_grex_fan_mode",
        "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/grex_fan/state",
        "value_template": "{{ value_json.fan_mode }}",
        "icon": "mdi:play-circle-outline",
        "unique_id": "test_grex_grex_fan_mode",
        "device": EXPECTED_DEVICE_INFO,
    }
    expected_speed_payload = {
        "name": "test_grex_fan_speed",
        "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/grex_fan/state",
        "value_template": "{{ value_json.fan_speed }}",
        "icon": "mdi:speedometer",
        "unique_id": "test_grex_grex_fan_speed",
        "device": EXPECTED_DEVICE_INFO,
    }
    assert json.loads(mode_payload_str) == expected_mode_payload
    assert json.loads(speed_payload_str) == expected_speed_payload


def test_controller_discovery_payloads_remove(controller):
    payloads = controller.get_discovery_payloads(remove=True)
    assert payloads == [
        (f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_mode/config", ""),
        (f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_speed/config", ""),
    ]


def test_controller_get_subscribe_topics(controller):
    assert controller.get_subscribe_topics() == [
        f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_mode/config",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_fan_speed/config",
    ]


# ---------------------------------------------------------------------------
# Controller.build_sensor_payload 매핑
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
def test_build_sensor_payload_fan_mode_mapping(controller, mode, ha_mode_on, expected_fan_mode):
    """mode(+ ha_mode_on 플래그)가 한글 fan_mode로 매핑된다."""
    payload = controller.build_sensor_payload(mode, "off", ha_mode_on=ha_mode_on)
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
def test_build_sensor_payload_fan_speed_mapping(controller, speed, expected_fan_speed):
    """speed가 한글 fan_speed로 매핑된다 (mode는 항상 통과되는 상태로 고정)."""
    payload = controller.build_sensor_payload("manual", speed, ha_mode_on=False)
    assert payload["fan_speed"] == expected_fan_speed


def test_build_sensor_payload_guard_blocks_when_off_and_ha_off(controller):
    """mode가 off이고 ha_mode_on도 False이면 가드에 걸려 off/off 그대로 반환한다."""
    payload = controller.build_sensor_payload("off", "low", ha_mode_on=False)
    assert payload == {"fan_mode": "off", "fan_speed": "off"}

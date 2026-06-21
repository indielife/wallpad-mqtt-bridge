import json
from unittest.mock import MagicMock

import pytest

from wallpad.mqtt import HA_CLIMATE, HA_FAN, HA_LIGHT, HA_PREFIX, HA_SENSOR, HA_SWITCH
from wallpad.panel.panel import WallpadPanel
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
)


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sw_version = "1.0.0"
    config.mqtt_config = {"server": "test", "username": "", "password": ""}
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.kocom_default_speed = "low"
    config.kocom_light_size = {"room1": 2}
    config.kocom_plug_size = {"room1": 1}
    config.kocom_room = {"00": "room1"}
    config.kocom_room_thermostat = {"00": "room1"}
    config.kocom_room_rev = {"room1": "00", "wallpad": "00"}
    config.kocom_room_thermostat_rev = {"room1": "00"}
    config.ventilator_default_speed = "low"
    return config


@pytest.fixture
def kocom_factory(mock_config):
    """활성화할 device를 지정해 WallpadPanel 인스턴스와 mock publish 검증용 리스트를 반환합니다."""
    published = []

    mock_mqtt = MagicMock()
    mock_mqtt.publish_json.side_effect = lambda topic, payload, **_: published.append(
        (topic, payload)
    )

    def _create(*active_devices: str):
        mock_config.wp_light = "light" in active_devices
        mock_config.wp_plug = "plug" in active_devices
        mock_config.wp_thermostat = "thermostat" in active_devices
        mock_config.wp_elevator = "elevator" in active_devices
        mock_config.wp_gas = "gas" in active_devices
        mock_config.wp_fan = "fan" in active_devices
        kocom = WallpadPanel(mock_config, mock_mqtt, MagicMock())
        published.clear()
        return kocom, published

    return _create


# ---------------------------------------------------------------------------
# _find_device
# ---------------------------------------------------------------------------


def test_find_device_returns_correct_instance(kocom_factory):
    """`_find_device`가 타입과 room이 일치하는 device를 반환하는지 검증합니다."""
    kocom, _ = kocom_factory("light")
    device = kocom._find_device(DEVICE_LIGHT, "room1")
    assert device is not None
    assert device.room == "room1"


def test_find_device_returns_none_for_unknown_type(kocom_factory):
    """등록되지 않은 device_type에 대해 None을 반환하는지 검증합니다."""
    kocom, _ = kocom_factory("light")
    assert kocom._find_device("unknown_device", "room1") is None


def test_find_device_returns_none_when_device_disabled(kocom_factory):
    """비활성화된 device에 대해 None을 반환하는지 검증합니다."""
    kocom, _ = kocom_factory("light")
    assert kocom._find_device(DEVICE_GAS, "wallpad") is None


# ---------------------------------------------------------------------------
# publish_state_to_ha
# ---------------------------------------------------------------------------


def test_publish_state_light(kocom_factory):
    kocom, published = kocom_factory("light")
    value = {"light1": "on", "light2": "off"}
    kocom.publish_state_to_ha(DEVICE_LIGHT, "room1", value)
    assert published == [(f"{HA_PREFIX}/{HA_LIGHT}/room1/state", value)]


def test_publish_state_plug(kocom_factory):
    kocom, published = kocom_factory("plug")
    value = {"plug1": "on"}
    kocom.publish_state_to_ha(DEVICE_PLUG, "room1", value)
    assert published == [(f"{HA_PREFIX}/{HA_SWITCH}/room1/state", value)]


def test_publish_state_thermostat(kocom_factory):
    kocom, published = kocom_factory("thermostat")
    value = {"mode": "heat", "target_temp": 22, "current_temp": 20}
    kocom.publish_state_to_ha(DEVICE_THERMOSTAT, "room1", value)
    assert published == [(f"{HA_PREFIX}/{HA_CLIMATE}/room1/state", value)]


def test_publish_state_elevator(kocom_factory):
    kocom, published = kocom_factory("elevator")
    kocom.publish_state_to_ha(DEVICE_ELEVATOR, "wallpad", "on")
    assert published == [(f"{HA_PREFIX}/{HA_SWITCH}/wallpad/state", {"elevator": "on"})]


def test_publish_state_gas_publishes_two_topics(kocom_factory):
    """Gas는 sensor와 switch 두 토픽 모두에 발행하는지 검증합니다."""
    kocom, published = kocom_factory("gas")
    kocom.publish_state_to_ha(DEVICE_GAS, "wallpad", "off")
    assert published == [
        (f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/state", {"gas": "off"}),
        (f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/state", {"gas": "off"}),
    ]


def test_publish_state_fan(kocom_factory):
    kocom, published = kocom_factory("fan")
    value = {"mode": "on", "speed": "low"}
    kocom.publish_state_to_ha(DEVICE_FAN, "wallpad", value)
    assert published == [(f"{HA_PREFIX}/{HA_FAN}/wallpad/state", value)]


def test_publish_state_no_op_when_device_not_found(kocom_factory):
    """device를 찾지 못한 경우 publish_json이 호출되지 않는지 검증합니다."""
    kocom, published = kocom_factory("light")
    kocom.publish_state_to_ha(DEVICE_GAS, "wallpad", "off")
    assert published == []

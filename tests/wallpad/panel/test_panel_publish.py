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


def _make_room(name, room_no=None, light_count=0, plug_count=0, thermo_no=None):
    r = MagicMock()
    r.name = name
    r.room_no = room_no
    r.light_count = light_count
    r.plug_count = plug_count
    r.thermo_no = thermo_no
    r.light_addr = f"{room_no:02d}" if room_no is not None else None
    r.thermo_addr = f"{thermo_no:02d}" if thermo_no is not None else None
    return r


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sw_version = "1.0.0"
    config.mqtt_config = {"server": "test", "username": "", "password": ""}
    config.init_temp = 22
    config.kocom_default_speed = "low"
    config.kocom_room_rev = {"room1": "00", "wallpad": "00"}
    config.kocom_room_thermostat_rev = {"room1": "00"}
    config.kocom_light_size = {"room1": 2}
    config.kocom_plug_size = {"room1": 1}
    config.ventilator_default_speed = "low"
    return config


@pytest.fixture
def panel_factory(mock_config):
    """활성화할 device를 지정해 WallpadPanel 인스턴스와 mock publish 검증용 리스트를 반환합니다."""
    published = []

    mock_mqtt = MagicMock()
    mock_mqtt.publish_json.side_effect = lambda topic, payload, **_: published.append(
        (topic, payload)
    )

    def _create(*active_devices: str):
        # 집 전체 단위 기기
        mock_config.elevator_enabled = "elevator" in active_devices
        mock_config.gas_enabled = "gas" in active_devices
        mock_config.fan_enabled = "fan" in active_devices

        # 방 기반 기기: active_devices에 맞는 rooms 구성
        room_no = 0 if ("light" in active_devices or "plug" in active_devices) else None
        thermo_no = 0 if "thermostat" in active_devices else None
        if room_no is not None or thermo_no is not None:
            mock_config.rooms = [
                _make_room(
                    "room1",
                    room_no=room_no,
                    light_count=2 if "light" in active_devices else 0,
                    plug_count=1 if "plug" in active_devices else 0,
                    thermo_no=thermo_no,
                )
            ]
        else:
            mock_config.rooms = []

        panel = WallpadPanel(mock_config, mock_mqtt, MagicMock())
        published.clear()
        return panel, published

    return _create


# ---------------------------------------------------------------------------
# _find_device
# ---------------------------------------------------------------------------


def test_find_device_returns_correct_instance(panel_factory):
    """`_find_device`가 타입과 room이 일치하는 device를 반환하는지 검증합니다."""
    panel, _ = panel_factory("light")
    device = panel._find_device(DEVICE_LIGHT, "room1")
    assert device is not None
    assert device.room == "room1"


def test_find_device_returns_none_for_unknown_type(panel_factory):
    """등록되지 않은 device_type에 대해 None을 반환하는지 검증합니다."""
    panel, _ = panel_factory("light")
    assert panel._find_device("unknown_device", "room1") is None


def test_find_device_returns_none_when_device_disabled(panel_factory):
    """비활성화된 device에 대해 None을 반환하는지 검증합니다."""
    panel, _ = panel_factory("light")
    assert panel._find_device(DEVICE_GAS, "wallpad") is None


# ---------------------------------------------------------------------------
# publish_state_to_ha
# ---------------------------------------------------------------------------


def test_publish_state_light(panel_factory):
    panel, published = panel_factory("light")
    value = {"light1": "on", "light2": "off"}
    panel.publish_state_to_ha(DEVICE_LIGHT, "room1", value)
    assert published == [(f"{HA_PREFIX}/{HA_LIGHT}/room1/state", value)]


def test_publish_state_plug(panel_factory):
    panel, published = panel_factory("plug")
    value = {"plug1": "on"}
    panel.publish_state_to_ha(DEVICE_PLUG, "room1", value)
    assert published == [(f"{HA_PREFIX}/{HA_SWITCH}/room1/state", value)]


def test_publish_state_thermostat(panel_factory):
    panel, published = panel_factory("thermostat")
    value = {"mode": "heat", "target_temp": 22, "current_temp": 20}
    panel.publish_state_to_ha(DEVICE_THERMOSTAT, "room1", value)
    assert published == [(f"{HA_PREFIX}/{HA_CLIMATE}/room1/state", value)]


def test_publish_state_elevator(panel_factory):
    panel, published = panel_factory("elevator")
    panel.publish_state_to_ha(DEVICE_ELEVATOR, "wallpad", "on")
    assert published == [(f"{HA_PREFIX}/{HA_SWITCH}/wallpad/state", {"elevator": "on"})]


def test_publish_state_gas_publishes_two_topics(panel_factory):
    """Gas는 sensor와 switch 두 토픽 모두에 발행하는지 검증합니다."""
    panel, published = panel_factory("gas")
    panel.publish_state_to_ha(DEVICE_GAS, "wallpad", "off")
    assert published == [
        (f"{HA_PREFIX}/{HA_SENSOR}/wallpad_gas/state", {"gas": "off"}),
        (f"{HA_PREFIX}/{HA_SWITCH}/wallpad_gas/state", {"gas": "off"}),
    ]


def test_publish_state_fan(panel_factory):
    panel, published = panel_factory("fan")
    value = {"mode": "on", "speed": "low"}
    panel.publish_state_to_ha(DEVICE_FAN, "wallpad", value)
    assert published == [(f"{HA_PREFIX}/{HA_FAN}/wallpad/state", value)]


def test_publish_state_no_op_when_device_not_found(panel_factory):
    """device를 찾지 못한 경우 publish_json이 호출되지 않는지 검증합니다."""
    panel, published = panel_factory("light")
    panel.publish_state_to_ha(DEVICE_GAS, "wallpad", "off")
    assert published == []

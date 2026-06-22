from unittest.mock import MagicMock

import pytest

from wallpad.panel.devices import Elevator, Fan, Gas, Light, Plug, Thermostat
from wallpad.panel.panel import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    WallpadPanel,
)


def _make_room(name, room_no=None, light_count=0, plug_count=0, thermo_no=None):
    """테스트용 RoomConfig MagicMock을 생성합니다."""
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
    """rooms 기반 새 config 구조의 모킹 객체입니다."""
    config = MagicMock()
    config.sw_version = "0.1.0"
    config.wallpad_manufacturer = "kocom"
    config.init_temp = 22
    config.kocom_default_speed = "low"

    # 방 설정: livingroom(조명3, 콘센트2, 난방), bedroom(조명2, 콘센트2, 난방), kitchen(조명3, 난방없음)
    config.rooms = [
        _make_room("livingroom", room_no=0, light_count=3, plug_count=2, thermo_no=0),
        _make_room("bedroom", room_no=1, light_count=2, plug_count=2, thermo_no=1),
        _make_room("kitchen", room_no=4, light_count=3, plug_count=2),
    ]

    # Fan/Gas/Elevator는 여전히 boolean
    config.fan_enabled = False
    config.gas_enabled = True
    config.elevator_enabled = False

    # 패킷 빌딩용 역방향 매핑
    config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "kitchen": "04",
        "wallpad": "00",
    }
    config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
    }

    return config


@pytest.fixture
def mock_transport():
    return MagicMock()


class TestWpListLight:
    def test_light_state_created_for_rooms(self, mock_config, mock_transport):
        """rooms에 있는 방에 대해 조명 상태가 초기화되는지 검증합니다."""
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        assert DEVICE_LIGHT in panel.device_states
        assert "livingroom" in panel.device_states[DEVICE_LIGHT]
        assert "bedroom" in panel.device_states[DEVICE_LIGHT]
        assert "kitchen" in panel.device_states[DEVICE_LIGHT]

    def test_light_subdevice_count_matches_light_count(self, mock_config, mock_transport):
        """light_count에 맞는 수의 서브기기(light1~N + light0)가 생성되는지 검증합니다."""
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        livingroom = panel.device_states[DEVICE_LIGHT]["livingroom"]
        assert "light0" in livingroom  # 전체 on/off 표시용
        assert "light1" in livingroom
        assert "light2" in livingroom
        assert "light3" in livingroom
        assert "light4" not in livingroom  # light_count=3이므로 4는 없음

        bedroom = panel.device_states[DEVICE_LIGHT]["bedroom"]
        assert "light2" in bedroom
        assert "light3" not in bedroom  # light_count=2이므로 3은 없음

    def test_light_initial_state_is_off(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        state = panel.device_states[DEVICE_LIGHT]["livingroom"]["light1"]
        assert state["state"] == "off"
        assert state["set"] == "off"


class TestWpListPlug:
    def test_plug_state_created_for_rooms(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        assert DEVICE_PLUG in panel.device_states
        assert "livingroom" in panel.device_states[DEVICE_PLUG]

    def test_plug_subdevice_count_matches_plug_count(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        livingroom = panel.device_states[DEVICE_PLUG]["livingroom"]
        assert "plug0" in livingroom
        assert "plug1" in livingroom
        assert "plug2" in livingroom
        assert "plug3" not in livingroom  # plug_count=2이므로 3은 없음

    def test_plug_initial_state_is_on(self, mock_config, mock_transport):
        """콘센트 초기 상태는 on입니다 (오작동 방지)."""
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        state = panel.device_states[DEVICE_PLUG]["livingroom"]["plug1"]
        assert state["state"] == "on"
        assert state["set"] == "on"


class TestWpListThermostat:
    def test_thermostat_only_for_rooms_with_thermo_no(self, mock_config, mock_transport):
        """thermo_no가 있는 방만 난방 상태가 초기화되는지 검증합니다."""
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        assert DEVICE_THERMOSTAT in panel.device_states
        assert "livingroom" in panel.device_states[DEVICE_THERMOSTAT]
        assert "bedroom" in panel.device_states[DEVICE_THERMOSTAT]
        assert "kitchen" not in panel.device_states[DEVICE_THERMOSTAT]  # thermo_no 없음

    def test_thermostat_initial_temp(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        state = panel.device_states[DEVICE_THERMOSTAT]["livingroom"]
        assert state["target_temp"]["state"] == mock_config.init_temp


class TestWpListGlobalDevices:
    def test_gas_in_wp_list_when_enabled(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)
        assert DEVICE_GAS in panel.device_states

    def test_fan_not_in_wp_list_when_disabled(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)
        assert DEVICE_FAN not in panel.device_states

    def test_elevator_not_in_wp_list_when_disabled(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)
        assert DEVICE_ELEVATOR not in panel.device_states


class TestDeviceObjects:
    def test_light_objects_created_per_subdevice(self, mock_config, mock_transport):
        """light_count에 맞게 Light 객체가 방별로 생성되는지 검증합니다."""
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        livingroom_lights = [
            d for d in panel.devices if isinstance(d, Light) and d.room == "livingroom"
        ]
        bedroom_lights = [d for d in panel.devices if isinstance(d, Light) and d.room == "bedroom"]

        assert len(livingroom_lights) == 4  # light0 ~ light3
        assert len(bedroom_lights) == 3  # light0 ~ light2

    def test_thermostat_objects_only_for_configured_rooms(self, mock_config, mock_transport):
        """thermo_no가 있는 방에만 Thermostat 객체가 생성되는지 검증합니다."""
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        thermostats = [d for d in panel.devices if isinstance(d, Thermostat)]
        thermostat_rooms = {d.room for d in thermostats}

        assert "livingroom" in thermostat_rooms
        assert "bedroom" in thermostat_rooms
        assert "kitchen" not in thermostat_rooms

    def test_gas_object_created_when_enabled(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        gas_devices = [d for d in panel.devices if isinstance(d, Gas)]
        assert len(gas_devices) == 1

    def test_fan_object_not_created_when_disabled(self, mock_config, mock_transport):
        panel = WallpadPanel(mock_config, MagicMock(), mock_transport)

        fan_devices = [d for d in panel.devices if isinstance(d, Fan)]
        assert len(fan_devices) == 0

from unittest.mock import MagicMock

import pytest

from wallpad.panel.panel import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    WallpadPanel,
)
from wallpad.panel.state import KocomStateManager


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
    """테스트용 설정 모킹"""
    config = MagicMock()
    config.sw_version = "0.1.0"
    config.wallpad_manufacturer = "kocom"

    # Advanced 세부 제어 설정
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.kocom_default_speed = "low"

    # 방 기반 기기: rooms 리스트
    config.rooms = [
        _make_room("livingroom", room_no=0, light_count=3, plug_count=2, thermo_no=0),
    ]

    # 집 전체 단위 기기 활성화 (기본값: 모두 비활성)
    config.fan_enabled = False
    config.gas_enabled = False
    config.elevator_enabled = False

    # 패킷 빌딩/파싱용 파생 매핑
    config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "wallpad": "00",
    }
    config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
    }
    config.kocom_room = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_room_thermostat = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_light_size = {"livingroom": 3}
    config.kocom_plug_size = {"livingroom": 2}

    return config


@pytest.fixture
def panel_instance(mock_config):
    """상위 흐름 테스트를 위해 최소한의 상태만 구성한 WallpadPanel 인스턴스"""
    panel = WallpadPanel.__new__(WallpadPanel)
    panel.config = mock_config
    panel.default_speed = "low"
    panel.ha_registry = False
    panel.kocom_scan = False
    panel.name = "kocom"

    # MQTT 모킹
    panel.d_mqtt = MagicMock()

    # wp_list 초기화 (KocomStateManager 구조)
    panel.wp_list = KocomStateManager()
    initial_states = {
        DEVICE_LIGHT: {
            "livingroom": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "light1": {"state": "off", "set": "off", "last": "state", "count": 0},
                "light2": {"state": "off", "set": "off", "last": "state", "count": 0},
                "light3": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
        DEVICE_PLUG: {
            "livingroom": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "plug1": {"state": "on", "set": "on", "last": "state", "count": 0},
                "plug2": {"state": "on", "set": "on", "last": "state", "count": 0},
            }
        },
        DEVICE_THERMOSTAT: {
            "livingroom": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "mode": {"state": "off", "set": "off", "last": "state", "count": 0},
                "current_temp": {"state": 0, "set": 0, "last": "state", "count": 0},
                "target_temp": {"state": 22, "set": 22, "last": "state", "count": 0},
            }
        },
        DEVICE_FAN: {
            "wallpad": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "mode": {"state": "off", "set": "off", "last": "state", "count": 0},
                "speed": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
        DEVICE_GAS: {
            "wallpad": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "gas": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
        DEVICE_ELEVATOR: {
            "wallpad": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "elevator": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
    }
    for device, rooms in initial_states.items():
        panel.wp_list[device] = rooms

    return panel

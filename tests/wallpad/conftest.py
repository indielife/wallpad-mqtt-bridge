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


@pytest.fixture
def mock_config():
    """테스트용 설정 모킹"""
    config = MagicMock()
    config.sw_version = "0.1.0"

    # 1. MQTT 설정
    config.mqtt_config = {"server": "test"}

    # 3. Wallpad 활성화 정보
    config.wp_light = True
    config.wp_fan = True
    config.wp_plug = True
    config.wp_gas = True
    config.wp_elevator = True
    config.wp_thermostat = True

    # 4. Advanced 세부 제어 설정
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.kocom_default_speed = "low"

    # 5. WallpadPanel 사이즈 및 방 이름 매핑 설정
    config.kocom_light_size = {"livingroom": 3}
    config.kocom_plug_size = {"livingroom": 2}
    config.kocom_room = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_room_thermostat = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "wallpad": "00",
    }
    config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
    }

    # 6. Ventilator(전열교환기) 설정
    config.ventilator_default_speed = "low"

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

from unittest.mock import MagicMock

import pytest

from kocom.kocom import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    Kocom,
)
from kocom.state import KocomStateManager


@pytest.fixture
def mock_config():
    """테스트용 설정 모킹"""
    config = MagicMock()
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.default_speed = "medium"
    config.kocom_light_size = {"livingroom": 3}
    config.kocom_plug_size = {"livingroom": 2}
    config.sw_version = "0.1.0"
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
    config.wp_light = True
    config.wp_fan = True
    config.wp_plug = True
    config.wp_gas = True
    config.wp_elevator = True
    config.wp_thermostat = True
    config.mqtt_config = {"server": "test", "anonymous": "True"}
    return config


@pytest.fixture
def kocom_instance(mock_config):
    """상위 흐름 테스트를 위해 최소한의 상태만 구성한 Kocom 인스턴스"""
    kocom = Kocom.__new__(Kocom)
    kocom.config = mock_config
    kocom.default_speed = "medium"
    kocom.ha_registry = False
    kocom.kocom_scan = False
    kocom._name = "kocom"
    kocom.connected = True

    # MQTT 및 시리얼 모킹
    kocom.d_mqtt = MagicMock()
    kocom.write = MagicMock()

    # wp_list 초기화 (KocomStateManager 구조)
    kocom.wp_list = KocomStateManager()
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
        kocom.wp_list[device] = rooms

    return kocom

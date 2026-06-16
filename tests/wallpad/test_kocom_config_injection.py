from unittest.mock import MagicMock, patch

import pytest

from wallpad.kocom.kocom import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    Kocom,
)


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sw_version = "0.1.0"
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.kocom_default_speed = "low"
    config.kocom_light_size = {"livingroom": 3}
    config.kocom_plug_size = {"livingroom": 2}
    config.kocom_room = {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room2",
        "03": "room1",
        "04": "kitchen",
    }
    config.kocom_room_thermostat = {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room1",
        "03": "room2",
    }
    config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "room2": "02",
        "room1": "03",
        "kitchen": "04",
        "wallpad": "00",
    }
    config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "room1": "02",
        "room2": "03",
    }
    config.ventilator_default_speed = "low"

    config.wp_light = True
    config.wp_fan = True
    config.wp_plug = True
    config.wp_gas = True
    config.wp_elevator = True
    config.wp_thermostat = True
    config.mqtt_config = {"server": "test", "anonymous": "True"}
    return config


@pytest.fixture
def mock_adapter():
    """ConnectionAdapter 모킹 객체입니다."""
    return MagicMock()


def test_kocom_initial_state(mock_config, mock_adapter):
    """Kocom 객체 생성 시 내부 상태와 설정값들이 정상적으로 초기화되는지 검증합니다."""
    with patch("wallpad.kocom.kocom.threading.Thread"):
        kocom = Kocom(mock_config, mock_adapter, "kocom", 42, MagicMock())

        # 1. 글로벌 변수 의존성 세팅 검증
        assert kocom.default_speed == "low"

        # 2. RS485(Config) 의존성 플래그 세팅 검증
        assert kocom.wp_light is True
        assert kocom.wp_fan is True
        assert kocom.wp_gas is True
        assert kocom.wp_elevator is True
        assert kocom.wp_plug is True
        assert kocom.wp_thermostat is True

        # 3. 조명 기기 자료구조 생성 검증 (KOCOM_LIGHT_SIZE, KOCOM_ROOM 조합)
        assert DEVICE_LIGHT in kocom.wp_list
        assert "livingroom" in kocom.wp_list[DEVICE_LIGHT]
        assert "light1" in kocom.wp_list[DEVICE_LIGHT]["livingroom"]
        assert "light2" in kocom.wp_list[DEVICE_LIGHT]["livingroom"]
        assert "light3" in kocom.wp_list[DEVICE_LIGHT]["livingroom"]

        # 4. 온도조절기 자료구조 및 초기 온도 생성 검증 (INIT_TEMP)
        assert DEVICE_THERMOSTAT in kocom.wp_list
        assert "livingroom" in kocom.wp_list[DEVICE_THERMOSTAT]
        # 기본 INIT_TEMP가 22로 잘 들어갔는지 검증
        assert kocom.wp_list[DEVICE_THERMOSTAT]["livingroom"]["target_temp"]["state"] == 22

        # 5. 기타 기기 자료구조 생성 검증
        assert DEVICE_FAN in kocom.wp_list
        assert DEVICE_GAS in kocom.wp_list
        assert DEVICE_ELEVATOR in kocom.wp_list

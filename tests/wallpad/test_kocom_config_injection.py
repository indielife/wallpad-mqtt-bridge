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


@pytest.fixture
def mock_config():
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

    # 6. Ventilator(전열교환기) 설정
    config.ventilator_default_speed = "low"

    return config


@pytest.fixture
def mock_transport():
    """BaseTransport 모킹 객체입니다."""
    return MagicMock()


def test_kocom_initial_state(mock_config, mock_transport):
    """WallpadPanel 객체 생성 시 내부 상태와 설정값들이 정상적으로 초기화되는지 검증합니다."""
    kocom = WallpadPanel(mock_config, MagicMock(), mock_transport)

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
    assert kocom.wp_list[DEVICE_THERMOSTAT]["livingroom"]["target_temp"]["state"] == 22

    # 5. 기타 기기 자료구조 생성 검증
    assert DEVICE_FAN in kocom.wp_list
    assert DEVICE_GAS in kocom.wp_list
    assert DEVICE_ELEVATOR in kocom.wp_list

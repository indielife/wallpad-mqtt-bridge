from unittest.mock import MagicMock, patch

import pytest

from kocom.core import (
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
    return MagicMock()


@pytest.fixture
def mock_rs485():
    """기존 RS485 객체의 역할을 흉내내는 모킹 객체입니다."""
    mock = MagicMock()
    mock._wp_light = True
    mock._wp_fan = True
    mock._wp_plug = True
    mock._wp_gas = True
    mock._wp_elevator = True
    mock._wp_thermostat = True
    mock._type = "serial"
    mock._connect = {"test_port": MagicMock()}
    mock._mqtt = {"server": "test", "anonymous": "True"}
    return mock


def test_kocom_initial_state(mock_config, mock_rs485):
    """Kocom 객체 생성 시 내부 상태와 설정값들이 정상적으로 초기화되는지 검증합니다."""
    with (
        patch("kocom.core.Kocom.connect_mqtt"),
        patch("kocom.core.threading.Thread"),
    ):
        kocom = Kocom(mock_config, mock_rs485, "kocom", "test_port", 42)

        # 1. 글로벌 변수 의존성 세팅 검증
        assert kocom.default_speed == "medium"

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

from unittest.mock import MagicMock

import pytest

from wallpad.ventilator.ventilator import Ventilator


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sw_version = "1.0.0"

    # 1. MQTT 설정
    config.mqtt_config = {"server": "test"}

    # 6. Ventilator(전열교환기) 설정
    config.ventilator_default_speed = "low"

    return config


@pytest.fixture
def mock_controller_transport():
    return MagicMock()


@pytest.fixture
def mock_ventilator_transport():
    return MagicMock()


def test_grex_initial_state(mock_config, mock_controller_transport, mock_ventilator_transport):
    """Ventilator 객체 생성 시 내부 상태와 통신 의존성들이 정상적으로 초기화되는지 검증합니다."""
    ventilator = Ventilator(
        mock_config, MagicMock(), mock_controller_transport, mock_ventilator_transport
    )

    # 1. 글로벌 변수 의존성 세팅 검증
    assert ventilator.default_speed == "low"

    # 2. 통신 연결 정보 및 디바이스 상태 객체 검증
    assert ventilator.controller_transport == mock_controller_transport
    assert ventilator.ventilator_transport == mock_ventilator_transport
    assert ventilator.grex_cont == {"mode": "off", "speed": "off"}
    assert ventilator.vent_cont == {"mode": "off", "speed": "off"}
    assert ventilator.mqtt_cont == {"mode": "off", "speed": "off"}
    assert ventilator.device is not None
    assert ventilator.device.name_prefix == "grex"


def test_grex_default_speed_fallback(
    mock_config, mock_controller_transport, mock_ventilator_transport
):
    """Ventilator 객체 생성 시 잘못된 default_speed가 주어지면 low로 강제 설정되는지 검증합니다."""
    mock_config.ventilator_default_speed = "invalid_speed"

    ventilator = Ventilator(
        mock_config, MagicMock(), mock_controller_transport, mock_ventilator_transport
    )

    assert ventilator.default_speed == "low"

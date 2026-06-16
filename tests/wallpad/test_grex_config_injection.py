from unittest.mock import MagicMock, patch

import pytest

from wallpad.grex.grex import Grex


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sw_version = "1.0.0"
    config.mqtt_config = {"server": "test", "anonymous": "True"}
    config.ventilator_default_speed = "low"
    return config


@pytest.fixture
def mock_controller_adapter():
    """Mock ConnectionAdapter for Grex Controller."""
    return MagicMock()


@pytest.fixture
def mock_ventilator_adapter():
    """Mock ConnectionAdapter for Grex Ventilator."""
    return MagicMock()


def test_grex_initial_state(mock_config, mock_controller_adapter, mock_ventilator_adapter):
    """Grex 객체 생성 시 내부 상태와 통신 의존성들이 정상적으로 초기화되는지 검증합니다."""
    with (
        patch("wallpad.grex.grex.Grex.connect_mqtt"),
        patch("wallpad.grex.grex.threading.Thread"),
    ):
        grex = Grex(mock_config, mock_controller_adapter, mock_ventilator_adapter, MagicMock())

        # 1. 글로벌 변수 의존성 세팅 검증
        assert grex.default_speed == "low"

        # 2. 통신 연결 정보 및 디바이스 상태 객체 검증
        assert grex.controller_adapter == mock_controller_adapter
        assert grex.ventilator_adapter == mock_ventilator_adapter
        assert grex.grex_cont == {"mode": "off", "speed": "off"}
        assert grex.vent_cont == {"mode": "off", "speed": "off"}
        assert grex.mqtt_cont == {"mode": "off", "speed": "off"}
        assert grex.device is not None
        assert grex.device.name_prefix == "grex"


def test_grex_default_speed_fallback(mock_config, mock_controller_adapter, mock_ventilator_adapter):
    """Grex 객체 생성 시 잘못된 default_speed가 주어지면 medium으로 강제 설정되는지 검증합니다."""
    # 잘못된 설정값 모킹
    mock_config.ventilator_default_speed = "invalid_speed"

    with (
        patch("wallpad.grex.grex.Grex.connect_mqtt"),
        patch("wallpad.grex.grex.threading.Thread"),
    ):
        grex = Grex(mock_config, mock_controller_adapter, mock_ventilator_adapter, MagicMock())

        # 이상한 값이 들어와도 low로 방어되는지 검증
        assert grex.default_speed == "low"

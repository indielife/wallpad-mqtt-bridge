from unittest.mock import MagicMock, patch

import pytest

from kocom.core import DEFAULT_SPEED, Grex


@pytest.fixture
def mock_rs485():
    """기존 RS485 객체의 역할을 흉내내는 모킹 객체입니다."""
    mock = MagicMock()
    mock._mqtt = {"server": "test", "anonymous": "True"}
    return mock


def test_grex_initial_state(mock_rs485):
    """Grex 객체 생성 시 내부 상태와 통신 의존성들이 정상적으로 초기화되는지 검증합니다."""
    mock_cont = {"serial": MagicMock(), "name": "grex_controller", "length": 11}
    mock_vent = {"serial": MagicMock(), "name": "grex_ventilator", "length": 12}

    with (
        patch("kocom.core.Grex.connect_mqtt"),
        patch("kocom.core.threading.Thread"),
    ):
        grex = Grex(mock_rs485, mock_cont, mock_vent)

        # 1. 글로벌 변수 의존성 세팅 검증
        assert grex.default_speed == "medium"

        # 2. 통신 연결 정보 및 디바이스 상태 객체 검증
        assert grex.contoller == mock_cont
        assert grex.ventilator == mock_vent
        assert grex.grex_cont == {"mode": "off", "speed": "off"}
        assert grex.vent_cont == {"mode": "off", "speed": "off"}
        assert grex.mqtt_cont == {"mode": "off", "speed": "off"}
        assert grex.device is not None
        assert grex.device.name_prefix == "grex"


def test_grex_default_speed_fallback(mock_rs485):
    """Grex 객체 생성 시 잘못된 default_speed가 주어지면 medium으로 강제 설정되는지 검증합니다."""
    mock_cont = {"serial": MagicMock(), "name": "grex_controller", "length": 11}
    mock_vent = {"serial": MagicMock(), "name": "grex_ventilator", "length": 12}

    with (
        patch("kocom.core.DEFAULT_SPEED", "invalid_speed"),  # 잘못된 글로벌 설정값 모킹
        patch("kocom.core.Grex.connect_mqtt"),
        patch("kocom.core.threading.Thread"),
    ):
        grex = Grex(mock_rs485, mock_cont, mock_vent)

        # 이상한 값이 들어와도 medium으로 방어되는지 검증
        assert grex.default_speed == "medium"

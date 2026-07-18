from unittest.mock import MagicMock

import pytest

from wallpad.apps.ventilator.ventilator import Ventilator


@pytest.fixture
def mock_controller_transport():
    return MagicMock()


@pytest.fixture
def mock_ventilator_transport():
    return MagicMock()


def test_ventilator_initial_state(
    mock_config, mock_controller_transport, mock_ventilator_transport
):
    """Ventilator 객체 생성 시 내부 상태와 통신 의존성들이 정상적으로 초기화되는지 검증합니다."""
    ventilator = Ventilator(
        mock_config, MagicMock(), mock_controller_transport, mock_ventilator_transport
    )

    # 1. 글로벌 변수 의존성 세팅 검증
    assert ventilator.default_speed == "low"

    # 2. 통신 연결 정보 및 디바이스 상태 객체 검증
    assert ventilator.controller_transport == mock_controller_transport
    assert ventilator.ventilator_transport == mock_ventilator_transport
    assert ventilator.state.controller_status == {"mode": "off", "speed": "off"}
    assert ventilator.state.ventilator_status == {"mode": "off", "speed": "off"}
    assert ventilator.state.desired == {"mode": "off", "speed": "off"}
    assert ventilator.unit is not None
    assert ventilator.unit.name_prefix == "grex"

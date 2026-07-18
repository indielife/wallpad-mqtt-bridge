from unittest.mock import MagicMock

import pytest

from wallpad.panel.panel import Panel
from wallpad.protocol.kocom.constants import DEVICE_LIGHT


@pytest.fixture
def panel_instance():
    """Panel.make_packet의 위임 동작을 테스트하기 위한 최소화된 패널 픽스처"""
    panel = Panel.__new__(Panel)

    mock_packet_builder = MagicMock()
    mock_packet_builder.build_scan_packet.return_value = "scan_packet"
    panel.packet_builder = mock_packet_builder

    mock_controller = MagicMock()
    mock_controller.make_packet.return_value = "command_packet"
    panel.controller_map = {(DEVICE_LIGHT, "livingroom"): mock_controller}

    return panel


def test_panel_make_packet_delegation(panel_instance):
    """일반 명령은 controller_map을 통해 대상 컨트롤러에 위임하는지 검증"""
    packet = panel_instance.make_packet(DEVICE_LIGHT, "livingroom", "상태", "light1", "on")

    # 1. 대상 컨트롤러의 make_packet이 호출되어야 함
    controller = panel_instance.controller_map[(DEVICE_LIGHT, "livingroom")]
    controller.make_packet.assert_called_once_with("상태", "light1", "on")

    # 2. 반환값이 그대로 전달되어야 함
    assert packet == "command_packet"


def test_panel_make_packet_scan(panel_instance):
    """'조회' 명령은 패킷 빌더를 통해 스캔 패킷을 생성하는지 검증"""
    packet = panel_instance.make_packet(DEVICE_LIGHT, "livingroom", "조회", "", "")

    # 1. 컨트롤러의 make_packet이 호출되지 않아야 함
    controller = panel_instance.controller_map[(DEVICE_LIGHT, "livingroom")]
    controller.make_packet.assert_not_called()

    # 2. packet_builder.build_scan_packet이 호출되어야 함
    panel_instance.packet_builder.build_scan_packet.assert_called_once_with(
        device=DEVICE_LIGHT, room="livingroom"
    )

    assert packet == "scan_packet"


def test_panel_make_packet_not_found(panel_instance):
    """맵에 없는 컨트롤러에 대해 None을 반환하는지 검증 (조회 예외)"""
    packet = panel_instance.make_packet("unknown", "unknown", "상태", "target", "value")
    assert packet is None

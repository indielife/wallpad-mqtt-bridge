import pytest

from kocom.main import Grex


@pytest.fixture
def grex_instance():
    """무거운 초기화를 우회한 Grex 인스턴스"""
    return Grex.__new__(Grex)


def test_grex_make_control_packet(grex_instance):
    """Grex의 컨트롤 패킷이 올바르게 조립되는지 검증합니다."""
    packet = grex_instance.make_control_packet("auto", "low")

    # "auto" -> "0100", "low" -> "0101", postfix -> "0001"
    assert packet.startswith("d08ae022010001010001")
    assert len(packet) == 22  # 10 bytes * 2 + checksum(2)


def test_grex_make_response_packet(grex_instance):
    """Grex의 응답 패킷이 올바르게 조립되는지 검증합니다."""
    packet = grex_instance.make_response_packet(1)

    # speed: 1 -> "0101", postfix -> "0000000100", prefix -> "d18be021"
    assert packet.startswith("d18be02101010000000100")
    assert len(packet) == 24  # 11 bytes * 2 + checksum(2)

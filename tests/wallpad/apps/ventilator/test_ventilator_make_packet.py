import pytest


@pytest.mark.parametrize(
    "mode, speed, expected_prefix",
    [
        ("auto", "low", "d08ae022010001010001"),
        ("manual", "medium", "d08ae022020002020001"),
        ("sleep", "high", "d08ae022030003030001"),
        ("off", "off", "d08ae022000000000000"),
    ],
)
def test_ventilator_make_control_packet(ventilator_instance, mode, speed, expected_prefix):
    """Grex의 컨트롤 패킷이 올바르게 조립되는지 검증합니다."""
    packet = ventilator_instance.unit.build_control_packet(mode, speed)

    assert packet.startswith(expected_prefix)
    assert len(packet) == 22  # 10 bytes * 2 + checksum(2)


@pytest.mark.parametrize(
    "mode, speed, expected_prefix",
    [
        ("manual", "low", "d18be02101010000000100"),
        ("manual", "medium", "d18be02102020000000100"),
        ("manual", "high", "d18be02103030000000100"),
        ("off", "off", "d18be02100000000000000"),
    ],
)
def test_ventilator_make_response_packet(ventilator_instance, mode, speed, expected_prefix):
    """Grex의 응답 패킷이 올바르게 조립되는지 검증합니다."""
    packet = ventilator_instance.unit.build_response_packet(mode, speed)

    assert packet.startswith(expected_prefix)
    assert len(packet) == 24  # 11 bytes * 2 + checksum(2)

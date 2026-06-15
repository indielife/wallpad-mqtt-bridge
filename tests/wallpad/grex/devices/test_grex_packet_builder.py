from wallpad.grex.devices.grex_packet_builder import GrexPacketBuilder


def test_grex_packet_builder_build_control():
    """GrexPacketBuilder가 컨트롤 제어 패킷을 올바르게 생성하는지 검증합니다."""
    builder = GrexPacketBuilder()

    packet = builder.build_control(mode_hex="0100", speed_hex="0101", postfix_hex="0001")

    # d0 8a e0 22 01 00 01 01 00 01 의 첫 바이트(d0) 제외 9바이트 합 % 256 = 90
    assert packet == "d08ae02201000101000190"


def test_grex_packet_builder_build_response():
    """GrexPacketBuilder가 응답 패킷을 올바르게 생성하는지 검증합니다."""
    builder = GrexPacketBuilder()

    packet = builder.build_response(speed_hex="0101", postfix_hex="0000000100")

    # d1 8b e0 21 01 01 00 00 00 01 00 의 첫 바이트(d1) 제외 10바이트 합 % 256 = 8f
    assert packet == "d18be021010100000001008f"

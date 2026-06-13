from kocom.devices.packet_builder import KocomPacketBuilder


def test_kocom_packet_builder_build():
    """KocomPacketBuilder가 주어진 부품으로 올바른 프레임과 체크섬을 생성하는지 검증합니다."""
    builder = KocomPacketBuilder()

    packet = builder.build(
        device="0e",
        room="00",
        dst="0100",
        cmd="00",
        value="ffff000000000000",
    )

    # 결과물: 헤더(10) + 기기(2) + 방(2) + 목적지(4) + 명령(2) + 데이터(16) + 체크섬(2) + 테일(4) = 42글자
    assert len(packet) == 42
    assert packet.startswith("aa5530bc000e00010000ffff000000000000")
    assert packet.endswith("0d0d")

from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder


def test_kocom_packet_builder_build():
    """KocomPacketBuilder가 주어진 부품으로 올바른 프레임과 체크섬을 생성하는지 검증합니다."""
    builder = KocomPacketBuilder()

    packet = builder.build(
        device_hex="0e",
        room_hex="00",
        dst_hex="0100",
        cmd_hex="00",
        value_hex="ffff000000000000",
    )

    # 결과물: 헤더(10) + 기기(2) + 방(2) + 목적지(4) + 명령(2) + 데이터(16) + 체크섬(2) + 테일(4) = 42글자
    assert len(packet) == 42
    assert packet.startswith("aa5530bc000e00010000ffff000000000000")
    assert packet.endswith("0d0d")


def test_kocom_packet_builder_encode():
    """encode()가 기기·방 이름으로부터 올바른 주소·명령 니블을 조립하는지 검증합니다."""
    builder = KocomPacketBuilder(
        room_rev={"livingroom": "00", "wallpad": "00"},
        room_thermostat_rev={"livingroom": "05"},
    )

    packet = builder.encode(
        src="light", dst="wallpad", room="livingroom", cmd="상태", value_hex="ffff000000000000"
    )
    assert packet.startswith("aa5530bc000e00010000ffff000000000000")

    # thermostat은 room_rev가 아닌 room_thermostat_rev로 room_hex를 계산해야 함
    thermostat_packet = builder.encode(
        src="thermostat", dst="wallpad", room="livingroom", cmd="상태", value_hex="0" * 16
    )
    assert thermostat_packet.startswith("aa5530bc003605")


def test_kocom_packet_builder_build_scan_packet():
    """KocomPacketBuilder가 조회(scan) 패킷을 올바르게 생성하는지 검증합니다."""
    builder = KocomPacketBuilder(
        room_rev={"livingroom": "00", "wallpad": "00"}, room_thermostat_rev={}
    )

    packet = builder.build_scan_packet(device="light", room="livingroom")

    assert packet.startswith("aa5530bc000e0001003a0000000000000000")
    assert packet.endswith("0d0d")

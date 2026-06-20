from unittest.mock import MagicMock

from wallpad.grex.grex import Grex
from wallpad.kocom.devices import Thermostat
from wallpad.kocom.kocom import DEVICE_THERMOSTAT, Kocom
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder


def test_kocom_check_sum_format():
    """Kocom 패킷의 체크섬이 2자리 16진수(02x)로 올바르게 포맷팅되는지 검증합니다."""
    kocom = Kocom.__new__(Kocom)  # 무거운 __init__ 을 우회하여 인스턴스 생성

    # 17바이트 중 1바이트를 09로 설정. v_sum = 0.
    # sum = 9 + 1 = 10 -> "0a" (16진수 1자리일 때 앞에 0이 채워져야 함)
    packet = "0900000000000000000000000000000000" + "00" + "0a"
    is_valid, chk_sum = kocom.check_sum(packet)

    assert is_valid is True
    assert chk_sum == "0a"


def test_kocom_make_packet_thermostat_temp_format():
    """보일러 목표 온도가 2자리 16진수(02x)로 올바르게 포맷팅되는지 검증합니다."""
    kocom = Kocom.__new__(Kocom)
    mock_config = MagicMock()
    mock_config.kocom_room = {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room2",
        "03": "room1",
        "04": "kitchen",
    }
    mock_config.kocom_room_thermostat = {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room1",
        "03": "room2",
    }
    mock_config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "room2": "02",
        "room1": "03",
        "kitchen": "04",
        "wallpad": "00",
    }
    mock_config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "room1": "02",
        "room2": "03",
    }
    kocom.config = mock_config
    kocom.wp_list = {
        DEVICE_THERMOSTAT: {"room1": {"mode": {"set": "heat"}, "target_temp": {"set": 25.0}}}
    }
    kocom.packet_builder = KocomPacketBuilder()
    kocom.devices = [
        Thermostat(
            name_prefix="test", room="room1", sw_version="1.0", packet_builder=kocom.packet_builder
        )
    ]

    packet = kocom.make_packet(DEVICE_THERMOSTAT, "room1", "상태", "", "")
    # 25도 -> 16진수 "19". 패킷의 value(20번째 인덱스) 앞 6글자가 "110019"여야 함
    assert packet[20:26] == "110019"

    # 9도일 경우 "09"로 패딩되는지 추가 검증
    kocom.wp_list[DEVICE_THERMOSTAT]["room1"]["target_temp"]["set"] = 9.0
    packet_single = kocom.make_packet(DEVICE_THERMOSTAT, "room1", "상태", "", "")
    assert packet_single[20:26] == "110009"


def test_grex_hex_to_list_format():
    """Grex 패킷 문자열이 0x 접두사가 붙은 리스트로 올바르게 변환되는지 검증합니다."""
    grex = Grex.__new__(Grex)
    assert grex.hex_to_list("d08a09") == ["0xd0", "0x8a", "0x09"]


def test_grex_checksum_format():
    """Grex의 체크섬 검증 포맷 로직을 검증합니다."""
    grex = Grex.__new__(Grex)

    packet_with_checksum = "d0080109"
    is_valid, chk_sum_hex = grex.validate_checksum(packet_with_checksum, 3)
    assert is_valid is True
    assert chk_sum_hex == "0x09"  # validate 과정에서는 내부적으로 "0x09"로 비교됨

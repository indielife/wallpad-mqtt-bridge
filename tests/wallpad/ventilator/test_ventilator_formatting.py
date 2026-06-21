from wallpad.ventilator.ventilator import Ventilator


def test_ventilator_hex_to_list_format():
    """Ventilator 패킷 문자열이 0x 접두사가 붙은 리스트로 올바르게 변환되는지 검증합니다."""
    ventilator = Ventilator.__new__(Ventilator)
    assert ventilator.hex_to_list("d08a09") == ["0xd0", "0x8a", "0x09"]


def test_ventilator_checksum_format():
    """Ventilator 체크섬 검증 포맷 로직을 검증합니다."""
    ventilator = Ventilator.__new__(Ventilator)

    packet_with_checksum = "d0080109"
    is_valid, chk_sum_hex = ventilator.validate_checksum(packet_with_checksum, 3)
    assert is_valid is True
    assert chk_sum_hex == "0x09"  # validate 과정에서는 내부적으로 "0x09"로 비교됨

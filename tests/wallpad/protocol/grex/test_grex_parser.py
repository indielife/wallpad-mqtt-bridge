"""GrexPacketParser 단위 테스트."""

import pytest

from wallpad.protocol.grex.parser import GrexPacketParser

# d0 8a 00 00 01 00 01 01 00 00 → sum(bytes[1..9])=141=0x8d
VALID_D08A = "d08a00000100010100008d"  # 11 bytes, mode=auto(0100), speed=low(0101)
INVALID_D08A = "d08a00000100010100000d"  # wrong checksum

# d1 8b 00 00 01 01 00 00 00 00 00 → sum(bytes[1..10])=141=0x8d
VALID_D18B = "d18b0000010100000000008d"  # 12 bytes, speed=low(0101)

# d0 0a 00 00 00 00 00 00 00 00 → sum(bytes[1..9])=10=0x0a
VALID_D00A = "d00a00000000000000000a"  # 11 bytes


@pytest.fixture
def parser():
    return GrexPacketParser()


# ── validate_checksum ──────────────────────────────────────────────────────────


def test_validate_checksum_d08a_valid(parser):
    """유효 d08a 패킷의 체크섬 검증이 True를 반환한다."""
    ok, _ = parser.validate_checksum(VALID_D08A)
    assert ok is True


def test_validate_checksum_d08a_invalid(parser):
    """체크섬 불일치 d08a 패킷이 False를 반환한다."""
    ok, _ = parser.validate_checksum(INVALID_D08A)
    assert ok is False


def test_validate_checksum_d18b_valid(parser):
    """유효 d18b 패킷의 체크섬 검증이 True를 반환한다."""
    ok, _ = parser.validate_checksum(VALID_D18B)
    assert ok is True


# ── parse_frame ────────────────────────────────────────────────────────────────


def test_parse_frame_d08a_mode_and_speed(parser):
    """d08a 패킷이 mode=auto, speed=low 로 파싱된다."""
    result = parser.parse_frame(VALID_D08A)
    assert result is not None
    assert result["type"] == "d08a"
    assert result["mode"] == "auto"
    assert result["speed"] == "low"


def test_parse_frame_d18b_speed(parser):
    """d18b 패킷이 speed=low 로 파싱된다."""
    result = parser.parse_frame(VALID_D18B)
    assert result is not None
    assert result["type"] == "d18b"
    assert result["speed"] == "low"


def test_parse_frame_d00a_returns_type_only(parser):
    """d00a 패킷은 type=d00a 만 반환한다."""
    result = parser.parse_frame(VALID_D00A)
    assert result is not None
    assert result["type"] == "d00a"


def test_parse_frame_unknown_prefix_returns_none(parser):
    """알 수 없는 프리픽스 패킷에 대해 None을 반환한다."""
    result = parser.parse_frame("abcd00000000000000000000")
    assert result is None

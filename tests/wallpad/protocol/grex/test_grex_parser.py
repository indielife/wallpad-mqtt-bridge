import pytest

from wallpad.protocol.grex.parser import GrexPacketParser


@pytest.fixture
def parser():
    return GrexPacketParser()


# --- Packet constants ---
# d08a (controller status): d0 8a e0 22 01 00 01 01 00 01 | checksum
# bytes[1:10]=138+224+34+1+0+1+1+0+1=400, 400%256=144=0x90
# packet[8:12]="0100"→mode=auto, packet[12:16]="0101"→speed=low
D08A_AUTO_LOW = "d08ae02201000101000190"

# d08a (manual/medium): d0 8a e0 22 02 00 02 02 00 00 | checksum
# bytes[1:10]=138+224+34+2+0+2+2+0+0=402, 402%256=146=0x92
D08A_MANUAL_MEDIUM = "d08ae02202000202000092"

# d08a (off): d0 8a e0 22 00 00 00 00 00 00 | checksum
# bytes[1:10]=138+224+34+0+0+0+0+0+0=396, 396%256=140=0x8c
D08A_OFF = "d08ae0220000000000008c"

# d18b (ventilator status): d1 8b e0 21 01 01 00 00 00 01 00 | checksum
# bytes[1:11]=139+224+33+1+1+0+0+0+1+0=399, 399%256=143=0x8f
# packet[8:12]="0101"→speed=low
D18B_LOW = "d18be021010100000001008f"

# bad checksum (last byte corrupted to ff)
BAD_D08A = D08A_AUTO_LOW[:-2] + "ff"


# --- validate_checksum ---


def test_validate_checksum_d08a_valid(parser):
    is_valid, chk = parser.validate_checksum(D08A_AUTO_LOW)
    assert is_valid is True
    assert chk == "0x90"


def test_validate_checksum_d18b_valid(parser):
    is_valid, chk = parser.validate_checksum(D18B_LOW)
    assert is_valid is True
    assert chk == "0x8f"


def test_validate_checksum_invalid(parser):
    is_valid, _ = parser.validate_checksum(BAD_D08A)
    assert is_valid is False


# --- parse_frame ---


def test_parse_frame_d08a_auto_low(parser):
    result = parser.parse_frame(D08A_AUTO_LOW)
    assert result["prefix"] == "d08a"
    assert result["mode"] == "auto"
    assert result["speed"] == "low"


def test_parse_frame_d08a_manual_medium(parser):
    result = parser.parse_frame(D08A_MANUAL_MEDIUM)
    assert result["mode"] == "manual"
    assert result["speed"] == "medium"


def test_parse_frame_d08a_off(parser):
    result = parser.parse_frame(D08A_OFF)
    assert result["mode"] == "off"
    assert result["speed"] == "off"


def test_parse_frame_d18b_low(parser):
    result = parser.parse_frame(D18B_LOW)
    assert result["prefix"] == "d18b"
    assert result["speed"] == "low"

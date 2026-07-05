"""KocomPacketParser 단위 테스트."""

from unittest.mock import MagicMock

import pytest

from wallpad.protocol.kocom.parser import KocomPacketParser

# ACK 조명 패킷: src=light(0e)/livingroom(00), dst=wallpad(01), light1=on
# sum(bytes[:17])=793, v_sum=0, checksum=(794)%256=0x1a
ACK_LIGHT = "aa5530dc000e00010000ff000000000000001a0d0d"

# ACK 팬 패킷: src=fan(48)/00, dst=wallpad(01), mode=on, speed=low(4)
# sum(bytes[:17])=677, v_sum=0, checksum=678%256=0xa6
ACK_FAN = "aa5530dc0048000100001100400000000000a60d0d"

# ACK 온도조절기 패킷: src=thermostat(36)/00, heat모드, set_temp=22(0x16), current=20(0x14)
# sum(bytes[:17])=637, v_sum=0, checksum=638%256=0x7e
ACK_THERMOSTAT = "aa5530dc00360001000011001600140000007e0d0d"

# SEND 패킷: src=wallpad(01)/00, dst=light(0e)/00, 상태, value=ffff...
# sum(bytes[:17])=1016, v_sum=0, checksum=1017%256=0xf9
SEND_PACKET = "aa5530bc000e00010000ffff000000000000f90d0d"

INVALID_CHECKSUM = "aa5530bc000e00010000ffff000000000000ff0d0d"


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.kocom_room = {"00": "livingroom", "01": "bedroom"}
    cfg.kocom_room_thermostat = {"00": "livingroom", "01": "bedroom"}
    cfg.kocom_light_size = {"livingroom": 3}
    cfg.kocom_plug_size = {"livingroom": 2}
    cfg.init_temp = 22
    return cfg


@pytest.fixture
def parser(mock_config):
    return KocomPacketParser(mock_config)


# ── validate_checksum ──────────────────────────────────────────────────────────


def test_validate_checksum_valid(parser):
    """유효 패킷의 체크섬 검증이 True를 반환한다."""
    ok, chk = parser.validate_checksum(SEND_PACKET)
    assert ok is True
    assert chk == "f9"


def test_validate_checksum_invalid(parser):
    """체크섬 불일치 패킷이 False를 반환한다."""
    ok, _ = parser.validate_checksum(INVALID_CHECKSUM)
    assert ok is False


# ── parse_frame: 타입/기기 필드 ───────────────────────────────────────────────


def test_parse_frame_send_type_returns_correct_fields(parser):
    """SEND 타입 패킷이 type=send / dst=light 로 파싱된다."""
    v = parser.parse_frame(SEND_PACKET)
    assert v is not None
    assert v["type"] == "send"
    assert v["dst_device"] == "light"
    assert v["src_device"] == "wallpad"


def test_parse_frame_ack_type_returns_correct_fields(parser):
    """ACK 타입 패킷이 type=ack / src=light 로 파싱된다."""
    v = parser.parse_frame(ACK_LIGHT)
    assert v is not None
    assert v["type"] == "ack"
    assert v["src_device"] == "light"
    assert v["dst_device"] == "wallpad"


# ── parse_frame: 기기별 값 파싱 ───────────────────────────────────────────────


def test_parse_frame_light_switch_values(parser):
    """ACK 조명 패킷이 light1=on, light2/3=off 로 파싱된다."""
    v = parser.parse_frame(ACK_LIGHT)
    assert v is not None
    assert v["value"]["light1"] == "on"
    assert v["value"]["light2"] == "off"
    assert v["value"]["light3"] == "off"
    assert v["value"]["light0"] == "on"


def test_parse_frame_fan_mode_and_speed(parser):
    """ACK 팬 패킷이 mode=on, speed=low 로 파싱된다."""
    v = parser.parse_frame(ACK_FAN)
    assert v is not None
    assert v["value"]["mode"] == "on"
    assert v["value"]["speed"] == "low"


def test_parse_frame_thermostat_heat_mode(parser):
    """ACK 온도조절기 패킷이 heat 모드, set_temp=22, current_temp=20 으로 파싱된다."""
    v = parser.parse_frame(ACK_THERMOSTAT)
    assert v is not None
    assert v["value"]["mode"] == "heat"
    assert v["value"]["target_temp"] == 22
    assert v["value"]["current_temp"] == 20


def test_parse_frame_invalid_packet_returns_none(parser):
    """파싱 불가능한 패킷에 대해 None을 반환한다."""
    v = parser.parse_frame("deadbeef")
    assert v is None


# ── parse_frame: 라우팅 타겟 판정 ───────────────────────────────────────────────


def test_parse_frame_target_routing_light(parser):
    """ACK 조명 패킷의 타겟은 src_device와 src_room으로 설정된다."""
    v = parser.parse_frame(ACK_LIGHT)
    assert v is not None
    assert v["update_target"]["device"] == "light"
    assert v["update_target"]["room"] == "livingroom"


def test_parse_frame_target_routing_fan(parser):
    """ACK 팬 패킷의 타겟 룸은 항상 wallpad로 설정된다."""
    v = parser.parse_frame(ACK_FAN)
    assert v is not None
    assert v["update_target"]["device"] == "fan"
    assert v["update_target"]["room"] == "wallpad"


def test_parse_frame_target_routing_elevator(parser):
    """SEND 엘리베이터 패킷의 타겟은 dst_device와 wallpad로 설정된다."""
    # 엘리베이터 SEND 패킷: type=bc(send), dst=44(elevator)
    packet = "aa5530bc0044000100000000000000000000020d0d"
    p = parser._parse_packet(packet)
    v = parser._value_packet(p)
    assert v is not None
    assert v["update_target"]["device"] == "elevator"
    assert v["update_target"]["room"] == "wallpad"

import pytest

from wallpad.protocol.kocom.parser import KocomPacketParser

# --- Test fixtures ---


@pytest.fixture
def parser():
    return KocomPacketParser(
        room={"00": "livingroom", "01": "bedroom"},
        room_thermostat={"00": "livingroom", "01": "bedroom"},
        light_size={"livingroom": 3},
        plug_size={"livingroom": 2},
        init_temp=22,
    )


# --- Packet constants ---
# send (wallpad → light, 조회):
# sum(first 17 bytes)=564, v_sum=0 → chksum=(564+1)%256=565%256="35"
SCAN_SEND = "aa5530bc000e0001003a0000000000000000350d0d"

# ack (light → wallpad, 상태, lights 1+2 on, 3 off):
# sum(17 bytes)=1048, v_sum=0 → chksum=(1048+1)%256=1049%256="19"
LIGHT_ACK_ON = "aa5530dc000e00010000ffff000000000000190d0d"

# ack (light → wallpad, 상태, all off):
# sum(17 bytes)=538, v_sum=0 → chksum=(538+1)%256=539%256="1b"
LIGHT_ACK_OFF = "aa5530dc000e000100000000000000000000" + "1b" + "0d0d"

# ack (fan → wallpad, mode=on, speed=low):
# value[0:2]="11" → on, value[4:5]="4" → low
# sum(17 bytes)=677, v_sum=0 → chksum=(677+1)%256=678%256="a6"
FAN_ACK = "aa5530dc004800010000" + "1100400000000000" + "a6" + "0d0d"

# ack (thermostat → wallpad, heat mode, target=22, current=20):
# value: [0:2]="11"(heat), [2:4]="00"(away_off), [4:6]="16"(target=22),
#        [6:8]="00", [8:10]="14"(current=20), rest="000000"
# sum(17 bytes)=637, v_sum=0 → chksum=(637+1)%256=638%256="7e"
THERMOSTAT_ACK_HEAT = "aa5530dc003600010000" + "1100160014000000" + "7e" + "0d0d"

# same packet but with bad checksum byte
BAD_CHECKSUM = SCAN_SEND[:36] + "ff" + SCAN_SEND[38:]


# --- validate_checksum ---


def test_validate_checksum_send_packet(parser):
    is_valid, chk = parser.validate_checksum(SCAN_SEND)
    assert is_valid is True
    assert chk == "35"


def test_validate_checksum_ack_packet(parser):
    is_valid, chk = parser.validate_checksum(LIGHT_ACK_ON)
    assert is_valid is True
    assert chk == "19"


def test_validate_checksum_invalid(parser):
    is_valid, _ = parser.validate_checksum(BAD_CHECKSUM)
    assert is_valid is False


# --- parse_frame ---


def test_parse_frame_send_extracts_correct_fields(parser):
    frame = parser.parse_frame(SCAN_SEND)
    assert frame["header"] == "aa55"
    assert frame["type"] == "30b"
    assert frame["dst_device"] == "0e"
    assert frame["dst_room"] == "00"
    assert frame["src_device"] == "01"
    assert frame["src_room"] == "00"
    assert frame["command"] == "3a"
    assert frame["value"] == "0000000000000000"


def test_parse_frame_ack_swaps_src_dst(parser):
    frame = parser.parse_frame(LIGHT_ACK_ON)
    assert frame["type"] == "30d"
    assert frame["src_device"] == "0e"
    assert frame["dst_device"] == "01"


# --- parse (full mapped result) ---


def test_parse_scan_command_maps_to_human_readable(parser):
    v = parser.parse(SCAN_SEND)
    assert v["type"] == "send"
    assert v["command"] == "조회"
    assert v["src_device"] == "wallpad"
    assert v["dst_device"] == "light"
    assert v["dst_room"] == "livingroom"


def test_parse_light_ack_returns_switch_dict(parser):
    v = parser.parse(LIGHT_ACK_ON)
    assert v["src_device"] == "light"
    assert v["src_room"] == "livingroom"
    assert v["value"]["light1"] == "on"
    assert v["value"]["light2"] == "on"
    assert v["value"]["light3"] == "off"
    assert v["value"]["light0"] == "on"


def test_parse_light_all_off(parser):
    v = parser.parse(LIGHT_ACK_OFF)
    assert v["value"]["light0"] == "off"
    assert v["value"]["light1"] == "off"
    assert v["value"]["light2"] == "off"
    assert v["value"]["light3"] == "off"


def test_parse_fan_ack_returns_mode_and_speed(parser):
    v = parser.parse(FAN_ACK)
    assert v["src_device"] == "fan"
    assert v["value"]["mode"] == "on"
    assert v["value"]["speed"] == "low"


def test_parse_thermostat_heat_mode(parser):
    v = parser.parse(THERMOSTAT_ACK_HEAT)
    assert v["src_device"] == "thermostat"
    assert v["value"]["mode"] == "heat"
    assert v["value"]["target_temp"] == 22
    assert v["value"]["current_temp"] == 20


def test_parse_thermostat_off_uses_init_temp(parser):
    # value: heat=off → mode="off", target_temp falls back to init_temp
    # sum(17 bytes)=620, v_sum=0 → chksum=(620+1)%256=621%256="6d"
    # value[0:2]="00"(off), [4:6]="16", [8:10]="14"
    thermo_off = "aa5530dc003600010000" + "0000160014000000" + "6d" + "0d0d"
    v = parser.parse(thermo_off)
    assert v["value"]["mode"] == "off"
    assert v["value"]["target_temp"] == 22  # falls back to init_temp

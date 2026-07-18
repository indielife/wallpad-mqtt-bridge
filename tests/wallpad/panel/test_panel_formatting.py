from unittest.mock import MagicMock

from wallpad.panel.devices import Thermostat, ThermostatController
from wallpad.panel.panel import DEVICE_THERMOSTAT, Panel
from wallpad.panel.state import RoomState, SubDeviceState
from wallpad.protocol.kocom import constants as kocom_const
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder
from wallpad.protocol.kocom.parser import KocomPacketParser


def test_panel_check_sum_format():
    """체크섬이 2자리 16진수(02x)로 올바르게 포맷팅되는지 검증합니다."""
    parser = KocomPacketParser(MagicMock())

    # 17바이트 중 1바이트를 09로 설정. v_sum = 0.
    # sum = 9 + 1 = 10 -> "0a" (16진수 1자리일 때 앞에 0이 채워져야 함)
    packet = "0900000000000000000000000000000000" + "00" + "0a"
    is_valid, chk_sum = parser.validate_checksum(packet)

    assert is_valid is True
    assert chk_sum == "0a"


def test_panel_make_packet_thermostat_temp_format():
    """보일러 목표 온도가 2자리 16진수(02x)로 올바르게 포맷팅되는지 검증합니다."""
    panel = Panel.__new__(Panel)
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
    panel.config = mock_config
    panel.packet_builder = KocomPacketBuilder(
        room_rev=mock_config.kocom_room_rev,
        room_thermostat_rev=mock_config.kocom_room_thermostat_rev,
    )
    thermo_state = RoomState()
    thermo_state["mode"] = SubDeviceState(state="heat", set_val="heat")
    thermo_state["target_temp"] = SubDeviceState(state=25.0, set_val=25.0)
    thermo_ctrl = ThermostatController(
        DEVICE_THERMOSTAT, "room1", state=thermo_state, packet_builder=panel.packet_builder
    )
    thermo_ctrl.add_sub_device(
        Thermostat(
            name_prefix="test",
            room="room1",
            sw_version="1.0",
            hw_info=kocom_const.HARDWARE,
        )
    )
    panel.controller_map = {(DEVICE_THERMOSTAT, "room1"): thermo_ctrl}

    packet = panel.make_packet(DEVICE_THERMOSTAT, "room1", "상태", "", "")
    # 25도 -> 16진수 "19". 패킷의 value(20번째 인덱스) 앞 6글자가 "110019"여야 함
    assert packet[20:26] == "110019"

    # 9도일 경우 "09"로 패딩되는지 추가 검증
    thermo_state["target_temp"].set = 9.0
    packet_single = panel.make_packet(DEVICE_THERMOSTAT, "room1", "상태", "", "")
    assert packet_single[20:26] == "110009"

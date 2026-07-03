from unittest.mock import MagicMock

import pytest

from wallpad.panel.devices import Elevator, Fan, Gas, Light, Thermostat
from wallpad.panel.panel import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_THERMOSTAT,
    Panel,
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder


@pytest.fixture
def panel_instance():
    """무거운 초기화를 우회하고 패킷 생성에 필요한 최소한의 상태만 구성한 Panel 인스턴스"""
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
    panel.device_states = {
        DEVICE_LIGHT: {
            "livingroom": {
                "light1": {"state": "off"},
                "light2": {"state": "on"},
                "light3": {"state": "off"},
            }
        },
        DEVICE_THERMOSTAT: {
            "room1": {
                "mode": {"set": "heat"},
                "target_temp": {"set": 25.0},
            }
        },
        DEVICE_FAN: {
            "wallpad": {
                "mode": {"set": "on"},
                "speed": {"set": "medium"},
            }
        },
    }
    panel.packet_builder = KocomPacketBuilder(
        room_rev=mock_config.kocom_room_rev,
        room_thermostat_rev=mock_config.kocom_room_thermostat_rev,
    )
    panel.devices = [
        Light(
            name_prefix="test",
            room="livingroom",
            sub_device="light1",
            sw_version="1.0",
            packet_builder=panel.packet_builder,
        ),
        Light(
            name_prefix="test",
            room="livingroom",
            sub_device="light2",
            sw_version="1.0",
            packet_builder=panel.packet_builder,
        ),
        Light(
            name_prefix="test",
            room="livingroom",
            sub_device="light3",
            sw_version="1.0",
            packet_builder=panel.packet_builder,
        ),
        Thermostat(
            name_prefix="test", room="room1", sw_version="1.0", packet_builder=panel.packet_builder
        ),
        Fan(name_prefix="test", sw_version="1.0", packet_builder=panel.packet_builder),
        Elevator(name_prefix="test", sw_version="1.0", packet_builder=panel.packet_builder),
        Gas(name_prefix="test", sw_version="1.0", packet_builder=panel.packet_builder),
    ]
    return panel


def test_make_packet_light(panel_instance):
    """조명(Light) 제어 시 방 안의 다른 조명 상태까지 포함하여 페이로드를 조립하는지 검증합니다."""
    # 거실(livingroom)의 1번 조명을 'on'으로 제어
    packet = panel_instance.make_packet(DEVICE_LIGHT, "livingroom", "상태", "light1", "on")

    expected_body = (
        "aa5530bc00"  # Header
        "0e"  # p_device: 0e (Light)
        "00"  # p_room: 00 (livingroom)
        "0100"  # p_dst: 0100 (Wallpad livingroom)
        "00"  # p_cmd: 00 (상태)
        "ffff000000000000"  # p_value: light1(타겟 켬=ff), light2(기존 켬=ff), light3(기존 끔=00)
    )
    assert packet.startswith(expected_body)
    assert packet.endswith("0d0d")  # Tail 검증
    assert len(packet) == len(expected_body) + 2 + 4  # 본문 + 체크섬(2자) + 테일(4자)


def test_make_packet_thermostat(panel_instance):
    """보일러(Thermostat) 제어 시 모드와 목표 온도를 기반으로 페이로드를 조립하는지 검증합니다."""
    # room1 보일러 제어 (모드: heat, 온도: 25도)
    packet = panel_instance.make_packet(DEVICE_THERMOSTAT, "room1", "상태", "", "")

    expected_body = (
        "aa5530bc00"  # Header
        "36"  # p_device: 36 (Thermostat)
        "02"  # p_room: 02 (room1)
        "0100"  # p_dst: 0100 (Wallpad livingroom)
        "00"  # p_cmd: 00 (상태)
        "1100190000000000"  # p_value: 1100(heat) + 19(25도) + 패딩
    )
    assert packet.startswith(expected_body)


def test_make_packet_elevator(panel_instance):
    """엘리베이터 호출 시 p_device와 p_dst가 특수하게 덮어쓰여지는지 검증합니다."""
    packet = panel_instance.make_packet(DEVICE_ELEVATOR, "wallpad", "상태", "elevator", "on")

    expected_body = (
        "aa5530bc00"  # Header
        "0100"  # p_device & p_room 강제 덮어쓰기 (Wallpad, livingroom)
        "4400"  # p_dst 강제 덮어쓰기 (Elevator, livingroom)
    )
    assert packet.startswith(expected_body)


def test_make_packet_gas(panel_instance):
    """가스 밸브 제어 시 p_cmd가 'off'로 강제되는지 검증합니다."""
    packet = panel_instance.make_packet(DEVICE_GAS, "wallpad", "상태", "gas", "off")

    expected_body = (
        "aa5530bc00"  # Header
        "2c"  # p_device: 2c (Gas)
        "00"  # p_room: 00 (wallpad)
        "0100"  # p_dst: 0100 (Wallpad wallpad)
        "02"  # p_cmd: 02 (off)
        "0000000000000000"  # p_value
    )
    assert packet.startswith(expected_body)


def test_make_packet_fan(panel_instance):
    """환기팬(Fan) 제어 시 모드와 풍속을 기반으로 페이로드를 조립하는지 검증합니다."""
    packet = panel_instance.make_packet(DEVICE_FAN, "wallpad", "상태", "fan", "on")

    expected_body = (
        "aa5530bc00"  # Header
        "48"  # p_device: 48 (Fan)
        "00"  # p_room: 00 (wallpad)
        "0100"  # p_dst: 0100 (Wallpad wallpad)
        "00"  # p_cmd: 00 (상태)
        "1100800000000000"  # p_value: 1100(on) + 8(medium) + 패딩
    )
    assert packet.startswith(expected_body)

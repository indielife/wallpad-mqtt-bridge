from unittest.mock import MagicMock

import pytest

from wallpad.panel.devices import (
    ElevatorController,
    FanController,
    GasController,
    LightController,
    PlugController,
    ThermostatController,
)
from wallpad.panel.state import RoomState, SubDeviceState
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder


@pytest.fixture
def packet_builder():
    room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "room2": "02",
        "room1": "03",
        "kitchen": "04",
        "wallpad": "00",
    }
    room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "room1": "02",
        "room2": "03",
    }
    return KocomPacketBuilder(room_rev=room_rev, room_thermostat_rev=room_thermostat_rev)


def test_switch_controller_make_packet_light(packet_builder):
    state = RoomState()
    state["light1"] = SubDeviceState(state="off")
    state["light2"] = SubDeviceState(state="on")
    state["light3"] = SubDeviceState(state="off")

    controller = LightController(
        DEVICE_LIGHT, "livingroom", state=state, packet_builder=packet_builder
    )

    packet = controller.make_packet("상태", "light1", "on")

    expected_body = (
        "aa5530bc00"  # Header
        "0e"  # p_device: 0e (Light)
        "00"  # p_room: 00 (livingroom)
        "0100"  # p_dst: 0100 (Wallpad livingroom)
        "00"  # p_cmd: 00 (상태)
        "ffff000000000000"  # p_value: light1(타겟 켬=ff), light2(기존 켬=ff), light3(기존 끔=00)
    )
    assert packet is not None
    assert packet.startswith(expected_body)
    assert packet.endswith("0d0d")
    assert len(packet) == len(expected_body) + 2 + 4


def test_switch_controller_make_packet_unknown_target_returns_none(packet_builder):
    state = RoomState()
    state["light1"] = SubDeviceState(state="off")

    controller = LightController(
        DEVICE_LIGHT, "livingroom", state=state, packet_builder=packet_builder
    )

    assert controller.make_packet("상태", "light9", "on") is None


def test_switch_controller_make_packet_plug(packet_builder):
    state = RoomState()
    state["plug1"] = SubDeviceState(state="on")
    state["plug2"] = SubDeviceState(state="off")

    controller = PlugController(
        DEVICE_PLUG, "livingroom", state=state, packet_builder=packet_builder
    )

    packet = controller.make_packet("상태", "plug2", "on")

    expected_body = (
        "aa5530bc00"
        "3b"  # p_device: Plug (3b)
        "00"  # p_room: 00 (livingroom)
        "0100"
        "00"
        "ffff000000000000"  # plug1(기존 켬=ff), plug2(타겟 켬=ff)
    )
    assert packet is not None
    assert packet.startswith(expected_body)


def test_thermostat_controller_make_packet(packet_builder):
    state = RoomState()
    state["mode"] = SubDeviceState(state="heat", set_val="heat")
    state["target_temp"] = SubDeviceState(state=25.0, set_val=25.0)

    controller = ThermostatController(
        DEVICE_THERMOSTAT, "room1", state=state, packet_builder=packet_builder
    )

    packet = controller.make_packet("상태", "", "")

    expected_body = (
        "aa5530bc00"
        "36"  # p_device: Thermostat
        "02"  # p_room: 02 (room1)
        "0100"
        "00"
        "1100190000000000"  # 1100(heat) + 19(25도)
    )
    assert packet is not None
    assert packet.startswith(expected_body)


def test_fan_controller_make_packet(packet_builder):
    state = RoomState()
    state["mode"] = SubDeviceState(state="on", set_val="on")
    state["speed"] = SubDeviceState(state="medium", set_val="medium")

    controller = FanController(DEVICE_FAN, "wallpad", state=state, packet_builder=packet_builder)

    packet = controller.make_packet("상태", "fan", "on")

    expected_body = (
        "aa5530bc00"
        "48"  # Fan
        "00"  # wallpad
        "0100"
        "00"
        "1100800000000000"  # on(1100) + medium(8)
    )
    assert packet is not None
    assert packet.startswith(expected_body)


def test_gas_controller_make_packet(packet_builder):
    state = RoomState()
    state["gas"] = SubDeviceState(state="off", set_val="off")

    controller = GasController(DEVICE_GAS, "wallpad", state=state, packet_builder=packet_builder)

    packet = controller.make_packet("상태", "gas", "off")

    expected_body = (
        "aa5530bc00"
        "2c"  # Gas
        "00"
        "0100"
        "02"  # off
        "0000000000000000"
    )
    assert packet is not None
    assert packet.startswith(expected_body)


def test_elevator_controller_make_packet(packet_builder):
    state = RoomState()
    state["elevator"] = SubDeviceState(state="off", set_val="off")

    controller = ElevatorController(
        DEVICE_ELEVATOR, "wallpad", state=state, packet_builder=packet_builder
    )

    packet = controller.make_packet("상태", "elevator", "on")

    expected_body = (
        "aa5530bc00"
        "0100"  # src=wallpad, livingroom 강제
        "4400"  # dst=elevator, livingroom 강제
        "01"  # on
        "0000000000000000"
    )
    assert packet is not None
    assert packet.startswith(expected_body)

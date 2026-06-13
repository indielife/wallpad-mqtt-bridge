import pytest

from kocom.devices import Elevator, Gas, KocomPacketBuilder, Light, Thermostat
from kocom.main import (
    DEVICE_ELEVATOR,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_THERMOSTAT,
    Kocom,
)


@pytest.fixture
def kocom_instance():
    """무거운 초기화를 우회하고 패킷 생성에 필요한 최소한의 상태만 구성한 Kocom 인스턴스"""
    kocom = Kocom.__new__(Kocom)
    kocom.wp_list = {
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
    }
    kocom.packet_builder = KocomPacketBuilder()
    kocom.devices = [
        Light(name_prefix="test", room="livingroom", sub_device="light1", sw_version="1.0"),
        Light(name_prefix="test", room="livingroom", sub_device="light2", sw_version="1.0"),
        Light(name_prefix="test", room="livingroom", sub_device="light3", sw_version="1.0"),
        Thermostat(name_prefix="test", room="room1", sw_version="1.0"),
        Elevator(name_prefix="test", sw_version="1.0", packet_builder=kocom.packet_builder),
        Gas(name_prefix="test", sw_version="1.0", packet_builder=kocom.packet_builder),
    ]
    return kocom


def test_make_packet_light(kocom_instance):
    """조명(Light) 제어 시 방 안의 다른 조명 상태까지 포함하여 페이로드를 조립하는지 검증합니다."""
    # 거실(livingroom)의 1번 조명을 'on'으로 제어
    packet = kocom_instance.make_packet(DEVICE_LIGHT, "livingroom", "상태", "light1", "on")

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


def test_make_packet_thermostat(kocom_instance):
    """보일러(Thermostat) 제어 시 모드와 목표 온도를 기반으로 페이로드를 조립하는지 검증합니다."""
    # room1 보일러 제어 (모드: heat, 온도: 25도)
    packet = kocom_instance.make_packet(DEVICE_THERMOSTAT, "room1", "상태", "", "")

    expected_body = (
        "aa5530bc00"  # Header
        "36"  # p_device: 36 (Thermostat)
        "02"  # p_room: 02 (room1)
        "0100"  # p_dst: 0100 (Wallpad livingroom)
        "00"  # p_cmd: 00 (상태)
        "1100190000000000"  # p_value: 1100(heat) + 19(25도) + 패딩
    )
    assert packet.startswith(expected_body)


def test_make_packet_elevator(kocom_instance):
    """엘리베이터 호출 시 p_device와 p_dst가 특수하게 덮어쓰여지는지 검증합니다."""
    packet = kocom_instance.make_packet(DEVICE_ELEVATOR, "wallpad", "상태", "elevator", "on")

    expected_body = (
        "aa5530bc00"  # Header
        "0100"  # p_device & p_room 강제 덮어쓰기 (Wallpad, livingroom)
        "4400"  # p_dst 강제 덮어쓰기 (Elevator, livingroom)
    )
    assert packet.startswith(expected_body)


def test_make_packet_gas(kocom_instance):
    """가스 밸브 제어 시 p_cmd가 'off'로 강제되는지 검증합니다."""
    packet = kocom_instance.make_packet(DEVICE_GAS, "wallpad", "상태", "gas", "off")

    expected_body = (
        "aa5530bc00"  # Header
        "2c"  # p_device: 2c (Gas)
        "00"  # p_room: 00 (wallpad)
        "0100"  # p_dst: 0100 (Wallpad wallpad)
        "02"  # p_cmd: 02 (off)
        "0000000000000000"  # p_value
    )
    assert packet.startswith(expected_body)

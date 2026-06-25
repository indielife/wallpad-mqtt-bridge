import asyncio
from unittest.mock import AsyncMock

import pytest

from wallpad.ventilator.ventilator import Ventilator

# grex_controller: 11바이트, 시작 바이트 d0, 체크섬 위치 index 10
# sum(bytes[1:10]) = 1+2+...+9 = 45 = 0x2d
VALID_GREX_CONTROLLER_PACKET = "d00102030405060708092d"

# grex_ventilator: 12바이트, 시작 바이트 d1, 체크섬 위치 index 11
# sum(bytes[1:11]) = 1+2+...+10 = 55 = 0x37
VALID_GREX_VENTILATOR_PACKET = "d10102030405060708090a37"

# grex_controller 구조이지만 체크섬이 틀린 패킷 (0xff ≠ 계산값 0x2d)
INVALID_CHECKSUM_PACKET = "d001020304050607080900ff"


@pytest.fixture
def vent_read():
    return Ventilator.__new__(Ventilator)


def _make_transport(hex_packet: str) -> AsyncMock:
    """hex_packet 바이트를 1바이트씩 반환하다가 패킷 완료 후 CancelledError를 발생시킵니다."""
    chunks = [bytes.fromhex(hex_packet[i : i + 2]) for i in range(0, len(hex_packet), 2)]
    transport = AsyncMock()
    transport.read.side_effect = chunks + [asyncio.CancelledError()]
    return transport


async def test_read_loop_grex_controller_dispatches_valid_packet(vent_read):
    """유효한 grex_controller 패킷이 조립되면 packet_parsing을 호출합니다."""
    transport = _make_transport(VALID_GREX_CONTROLLER_PACKET)
    vent_read.packet_parsing = AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        await vent_read.get_serial(transport, "grex_controller", 11)

    vent_read.packet_parsing.assert_awaited_once_with(
        VALID_GREX_CONTROLLER_PACKET, "grex_controller"
    )


async def test_read_loop_grex_ventilator_dispatches_valid_packet(vent_read):
    """유효한 grex_ventilator 패킷이 조립되면 packet_parsing을 호출합니다."""
    transport = _make_transport(VALID_GREX_VENTILATOR_PACKET)
    vent_read.packet_parsing = AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        await vent_read.get_serial(transport, "grex_ventilator", 12)

    vent_read.packet_parsing.assert_awaited_once_with(
        VALID_GREX_VENTILATOR_PACKET, "grex_ventilator"
    )


async def test_read_loop_ignores_bytes_before_start_byte(vent_read):
    """시작 바이트(d0) 이전의 쓰레기 데이터는 무시하고 유효 패킷만 처리합니다."""
    transport = _make_transport("0102" + VALID_GREX_CONTROLLER_PACKET)
    vent_read.packet_parsing = AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        await vent_read.get_serial(transport, "grex_controller", 11)

    vent_read.packet_parsing.assert_awaited_once_with(
        VALID_GREX_CONTROLLER_PACKET, "grex_controller"
    )


async def test_read_loop_skips_packet_with_invalid_checksum(vent_read):
    """체크섬이 유효하지 않은 패킷은 packet_parsing을 호출하지 않습니다."""
    transport = _make_transport(INVALID_CHECKSUM_PACKET)
    vent_read.packet_parsing = AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        await vent_read.get_serial(transport, "grex_controller", 11)

    vent_read.packet_parsing.assert_not_awaited()

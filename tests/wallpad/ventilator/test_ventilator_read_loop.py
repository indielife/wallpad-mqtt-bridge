"""Ventilator._read_loop 수신 루프 단위 테스트."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from wallpad.protocol.grex.parser import GrexPacketParser
from wallpad.ventilator.ventilator import Ventilator

# d0 8a 00 00 01 00 01 01 00 00 → sum(bytes[1..9])=141=0x8d
VALID_D08A = "d08a00000100010100008d"  # grex_controller (11 bytes)
INVALID_D08A = "d08a00000100010100000d"  # wrong checksum

# d1 8b 00 00 01 01 00 00 00 00 00 → sum(bytes[1..10])=141=0x8d
VALID_D18B = "d18b0000010100000000008d"  # grex_ventilator (12 bytes)


def _byte_seq(hex_str: str, stop: Exception | None = None) -> list:
    seq: list = [bytes.fromhex(hex_str[i : i + 2]) for i in range(0, len(hex_str), 2)]
    if stop is not None:
        seq.append(stop)
    return seq


@pytest.fixture
def ventilator():
    v = Ventilator.__new__(Ventilator)
    v.packet_parsing = AsyncMock()
    v._parser = GrexPacketParser()
    return v


async def test_grex_controller_valid_packet_dispatched(ventilator):
    """grex_controller 유효 패킷 수신 시 packet_parsing이 호출된다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(VALID_D08A, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator._read_loop(transport, "grex_controller", 11)

    ventilator.packet_parsing.assert_called_once_with(VALID_D08A, "grex_controller")


async def test_grex_ventilator_valid_packet_dispatched(ventilator):
    """grex_ventilator 유효 패킷 수신 시 packet_parsing이 호출된다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(VALID_D18B, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator._read_loop(transport, "grex_ventilator", 12)

    ventilator.packet_parsing.assert_called_once_with(VALID_D18B, "grex_ventilator")


async def test_garbage_before_start_byte_ignored(ventilator):
    """시작 바이트 이전 쓰레기 데이터는 무시하고 유효 패킷만 dispatch한다."""
    garbage = "b1b2b3"
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(garbage + VALID_D08A, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator._read_loop(transport, "grex_controller", 11)

    ventilator.packet_parsing.assert_called_once_with(VALID_D08A, "grex_controller")


async def test_invalid_checksum_not_dispatched(ventilator):
    """체크섬 불일치 패킷은 packet_parsing이 호출되지 않는다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(INVALID_D08A, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator._read_loop(transport, "grex_controller", 11)

    ventilator.packet_parsing.assert_not_called()

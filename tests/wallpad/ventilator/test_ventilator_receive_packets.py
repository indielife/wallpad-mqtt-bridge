"""Ventilator.receive_packets 수신 루프 단위 테스트."""

import asyncio
from unittest.mock import AsyncMock

import pytest

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
def ventilator(ventilator_instance):
    ventilator_instance.dispatch_packet = AsyncMock()
    return ventilator_instance


async def test_grex_controller_valid_packet_dispatched(ventilator):
    """grex_controller 유효 패킷 수신 시 dispatch_packet이 호출된다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(VALID_D08A, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator.receive_packets(transport, "grex_controller")

    ventilator.dispatch_packet.assert_called_once_with(VALID_D08A, "grex_controller")


async def test_grex_ventilator_valid_packet_dispatched(ventilator):
    """grex_ventilator 유효 패킷 수신 시 dispatch_packet이 호출된다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(VALID_D18B, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator.receive_packets(transport, "grex_ventilator")

    ventilator.dispatch_packet.assert_called_once_with(VALID_D18B, "grex_ventilator")


async def test_garbage_before_start_byte_ignored(ventilator):
    """시작 바이트 이전 쓰레기 데이터는 무시하고 유효 패킷만 dispatch한다."""
    garbage = "b1b2b3"
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(garbage + VALID_D08A, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator.receive_packets(transport, "grex_controller")

    ventilator.dispatch_packet.assert_called_once_with(VALID_D08A, "grex_controller")


async def test_invalid_checksum_not_dispatched(ventilator):
    """체크섬 불일치 패킷은 dispatch_packet이 호출되지 않는다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(INVALID_D08A, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator.receive_packets(transport, "grex_controller")

    ventilator.dispatch_packet.assert_not_called()


async def test_mixed_d0_d1_packets_on_single_transport(ventilator):
    """단일 transport에서 d0, d1 패킷이 섞여 와도 각각 올바르게 dispatch된다."""
    transport = AsyncMock()
    transport.read.side_effect = _byte_seq(VALID_D08A + VALID_D18B, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await ventilator.receive_packets(transport, "grex")

    assert ventilator.dispatch_packet.call_count == 2
    ventilator.dispatch_packet.assert_any_call(VALID_D08A, "grex")
    ventilator.dispatch_packet.assert_any_call(VALID_D18B, "grex")

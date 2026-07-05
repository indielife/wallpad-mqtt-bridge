"""Panel.receive_packets 단위 테스트."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from wallpad.panel.panel import Panel
from wallpad.protocol.kocom.parser import KocomPacketParser

# sum(bytes[:17])=1016, v_sum=0, checksum=(1016+1+0)%256=0xf9
VALID_PACKET = "aa5530bc000e00010000ffff000000000000f90d0d"
INVALID_CHECKSUM = "aa5530bc000e00010000ffff000000000000ff0d0d"


def _byte_seq(hex_str: str, stop: Exception | None = None) -> list:
    seq: list = [bytes.fromhex(hex_str[i : i + 2]) for i in range(0, len(hex_str), 2)]
    if stop is not None:
        seq.append(stop)
    return seq


@pytest.fixture
def panel():
    p = Panel.__new__(Panel)
    p.tick = 0.0
    p.name = "kocom"
    p.transport = AsyncMock()
    p.process_packet = MagicMock()
    cfg = MagicMock()
    p.parser = KocomPacketParser(cfg)
    return p


async def test_valid_packet_dispatched(panel):
    """유효 패킷 수신 시 process_packet이 정확히 한 번 호출된다."""
    panel.transport.read.side_effect = _byte_seq(VALID_PACKET, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()

    panel.process_packet.assert_called_once_with(VALID_PACKET)


async def test_garbage_before_start_byte_ignored(panel):
    """시작 바이트 이전 쓰레기 데이터는 무시하고 유효 패킷만 dispatch한다."""
    garbage = "b1b2b3"
    panel.transport.read.side_effect = _byte_seq(garbage + VALID_PACKET, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()

    panel.process_packet.assert_called_once_with(VALID_PACKET)


async def test_invalid_checksum_not_dispatched(panel):
    """체크섬이 불일치하는 패킷은 process_packet이 호출되지 않는다."""
    panel.transport.read.side_effect = _byte_seq(INVALID_CHECKSUM, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()

    panel.process_packet.assert_not_called()


async def test_two_valid_packets_dispatched(panel):
    """연속된 두 유효 패킷이 각각 한 번씩 dispatch된다."""
    panel.transport.read.side_effect = _byte_seq(VALID_PACKET * 2, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()

    assert panel.process_packet.call_count == 2


async def test_sof_byte_in_payload_does_not_break_frame(panel):
    """패킷 페이로드 내부에 SOF의 첫 바이트가 나타나도 프레임이 깨지지 않는다."""
    valid_packet_with_aa = "aa5530bc000e00010000aa00000000000000a50d0d"
    panel.transport.read.side_effect = _byte_seq(valid_packet_with_aa, asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()

    panel.process_packet.assert_called_once_with(valid_packet_with_aa)

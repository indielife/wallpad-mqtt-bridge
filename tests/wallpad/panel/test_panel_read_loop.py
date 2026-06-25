import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from wallpad.panel.panel import WallpadPanel

# 유효한 KOCOM 조명 ACK 패킷 (체크섬 0x0e 적용)
# 구조: aa55 30d 0 00 0e(light) 00(livingroom) 01(wallpad) 00 00(state)
#        ff000000000000(value) 00(v_sum) 0e(checksum) 0d0d(tail)
VALID_KOCOM_PACKET = "aa5530d0000e00010000ff000000000000000e0d0d"

# 동일 구조이지만 체크섬이 틀린 패킷 (0x00 ≠ 계산값 0x0e)
INVALID_CHECKSUM_PACKET = "aa5530d0000e00010000ff00000000000000000d0d"


@pytest.fixture
def panel_read():
    panel = WallpadPanel.__new__(WallpadPanel)
    panel.transport = AsyncMock()
    return panel


def _setup_transport(transport: AsyncMock, hex_packet: str) -> None:
    """hex_packet 바이트를 1바이트씩 반환하다가 패킷 완료 후 CancelledError를 발생시킵니다."""
    chunks = [bytes.fromhex(hex_packet[i : i + 2]) for i in range(0, len(hex_packet), 2)]
    transport.read.side_effect = chunks + [asyncio.CancelledError()]


async def test_read_loop_dispatches_valid_packet(panel_read):
    """유효한 체크섬을 가진 패킷이 조립되면 packet_parsing을 호출합니다."""
    _setup_transport(panel_read.transport, VALID_KOCOM_PACKET)

    with patch.object(panel_read, "packet_parsing") as mock_parse:
        with pytest.raises(asyncio.CancelledError):
            await panel_read.get_serial("kocom", 42)

    mock_parse.assert_called_once_with(VALID_KOCOM_PACKET)


async def test_read_loop_ignores_bytes_before_start_byte(panel_read):
    """시작 바이트(aa) 이전의 쓰레기 데이터는 무시하고 유효 패킷만 처리합니다."""
    _setup_transport(panel_read.transport, "0102" + VALID_KOCOM_PACKET)

    with patch.object(panel_read, "packet_parsing") as mock_parse:
        with pytest.raises(asyncio.CancelledError):
            await panel_read.get_serial("kocom", 42)

    mock_parse.assert_called_once_with(VALID_KOCOM_PACKET)


async def test_read_loop_skips_packet_with_invalid_checksum(panel_read):
    """체크섬이 유효하지 않은 패킷은 packet_parsing을 호출하지 않습니다."""
    _setup_transport(panel_read.transport, INVALID_CHECKSUM_PACKET)

    with patch.object(panel_read, "packet_parsing") as mock_parse:
        with pytest.raises(asyncio.CancelledError):
            await panel_read.get_serial("kocom", 42)

    mock_parse.assert_not_called()

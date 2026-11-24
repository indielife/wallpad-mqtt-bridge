from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wallpad.transport.socket import SocketTransport


@pytest.fixture
def transport():
    return SocketTransport("192.168.1.1", 8899)


@pytest.fixture
def connected_transport(transport):
    transport._reader = AsyncMock()
    transport._writer = MagicMock(drain=AsyncMock())
    return transport


async def test_connect_opens_connection(transport):
    reader = AsyncMock()
    writer = MagicMock(drain=AsyncMock())
    with patch(
        "wallpad.transport.socket.asyncio.open_connection",
        return_value=(reader, writer),
    ) as mock_open:
        await transport.connect()

    mock_open.assert_called_once_with("192.168.1.1", 8899)
    assert transport._reader is reader
    assert transport._writer is writer


async def test_read_delegates_to_reader(connected_transport):
    connected_transport._reader.read.return_value = b"\xcc\xdd"

    result = await connected_transport.read(2)

    connected_transport._reader.read.assert_called_once_with(2)
    assert result == b"\xcc\xdd"


async def test_write_sends_data_and_drains(connected_transport):
    await connected_transport.write(b"\x01\x02")

    connected_transport._writer.write.assert_called_once_with(b"\x01\x02")
    connected_transport._writer.drain.assert_awaited_once()


async def test_close_closes_writer(connected_transport):
    await connected_transport.close()

    connected_transport._writer.close.assert_called_once()


async def test_socket_eof_is_connection_loss(connected_transport):
    connected_transport._reader.read.return_value = b""
    with pytest.raises(ConnectionError, match="EOF"):
        await connected_transport.read(1)


async def test_socket_zero_length_read_is_not_eof(connected_transport):
    connected_transport._reader.read.return_value = b""
    assert await connected_transport.read(0) == b""


async def test_eof_reconnects_through_existing_wrapper(connected_transport, caplog):
    from wallpad.transport.reconnect import ReconnectingTransport

    connected_transport._reader.read.side_effect = [b"", b"\xaa"]
    connected_transport.connect = AsyncMock()
    transport = ReconnectingTransport(connected_transport)
    with patch("wallpad.transport.reconnect.asyncio.sleep"):
        assert await transport.read(1) == b"\xaa"
    connected_transport.connect.assert_awaited_once()
    assert "EOF" in caplog.text

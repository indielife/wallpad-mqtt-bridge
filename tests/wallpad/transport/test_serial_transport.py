from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wallpad.transport.serial import SerialTransport


@pytest.fixture
def transport():
    return SerialTransport("/dev/ttyUSB0", 9600)


@pytest.fixture
def connected_transport(transport):
    transport._reader = AsyncMock()
    transport._writer = MagicMock(drain=AsyncMock())
    return transport


async def test_connect_opens_serial_connection(transport):
    reader = AsyncMock()
    writer = MagicMock(drain=AsyncMock())
    with patch(
        "wallpad.transport.serial.serial_asyncio.open_serial_connection",
        return_value=(reader, writer),
    ) as mock_open:
        await transport.connect()

    mock_open.assert_called_once_with(url="/dev/ttyUSB0", baudrate=9600)
    assert transport._reader is reader
    assert transport._writer is writer


async def test_read_delegates_to_reader(connected_transport):
    connected_transport._reader.read.return_value = b"\xaa\xbb"

    result = await connected_transport.read(2)

    connected_transport._reader.read.assert_called_once_with(2)
    assert result == b"\xaa\xbb"


async def test_write_sends_data_and_drains(connected_transport):
    await connected_transport.write(b"\x01\x02\x03")

    connected_transport._writer.write.assert_called_once_with(b"\x01\x02\x03")
    connected_transport._writer.drain.assert_awaited_once()


async def test_close_closes_writer(connected_transport):
    await connected_transport.close()

    connected_transport._writer.close.assert_called_once()

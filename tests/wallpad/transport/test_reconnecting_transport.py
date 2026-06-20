from unittest.mock import AsyncMock, call, patch

import pytest

from wallpad.transport.reconnect import ReconnectingTransport


@pytest.fixture
def inner():
    return AsyncMock()


@pytest.fixture
def transport(inner):
    return ReconnectingTransport(inner, reconnect_interval=5.0)


async def test_connect_delegates(transport, inner):
    await transport.connect()
    inner.connect.assert_awaited_once()


async def test_close_delegates(transport, inner):
    await transport.close()
    inner.close.assert_awaited_once()


async def test_read_returns_data(transport, inner):
    inner.read.return_value = b"\xaa"

    result = await transport.read(1)

    assert result == b"\xaa"
    inner.read.assert_awaited_once_with(1)


async def test_write_sends_data(transport, inner):
    await transport.write(b"\x01\x02")

    inner.write.assert_awaited_once_with(b"\x01\x02")


async def test_read_reconnects_on_error(transport, inner):
    inner.read.side_effect = [OSError("connection lost"), b"\xaa"]

    with patch("wallpad.transport.reconnect.asyncio.sleep"):
        result = await transport.read(1)

    assert result == b"\xaa"
    inner.close.assert_awaited_once()
    inner.connect.assert_awaited_once()


async def test_write_reconnects_on_error(transport, inner):
    inner.write.side_effect = [OSError("connection lost"), None]

    with patch("wallpad.transport.reconnect.asyncio.sleep"):
        await transport.write(b"\x01")

    inner.close.assert_awaited_once()
    inner.connect.assert_awaited_once()
    assert inner.write.await_args_list == [call(b"\x01"), call(b"\x01")]


async def test_reconnect_sleeps_for_interval(transport, inner):
    inner.read.side_effect = [OSError("disconnected"), b"\xbb"]

    with patch("wallpad.transport.reconnect.asyncio.sleep") as mock_sleep:
        await transport.read(1)

    mock_sleep.assert_awaited_once_with(5.0)


async def test_reconnect_retries_until_connected(transport, inner):
    inner.read.side_effect = [OSError("disconnected"), b"\xff"]
    inner.connect.side_effect = [OSError("still down"), None]

    with patch("wallpad.transport.reconnect.asyncio.sleep"):
        result = await transport.read(1)

    assert result == b"\xff"
    assert inner.connect.await_count == 2
    assert inner.close.await_count == 2


async def test_reconnect_ignores_close_error(transport, inner):
    inner.read.side_effect = [OSError("disconnected"), b"\xcc"]
    inner.close.side_effect = [OSError("close failed"), None]

    with patch("wallpad.transport.reconnect.asyncio.sleep"):
        result = await transport.read(1)

    assert result == b"\xcc"

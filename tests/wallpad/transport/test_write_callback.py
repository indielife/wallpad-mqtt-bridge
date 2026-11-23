"""전송 계층의 쓰기 알림은 바이트 쓰기와 drain 사이의 경계를 나타낸다."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wallpad.transport.serial import SerialTransport
from wallpad.transport.socket import SocketTransport


@pytest.fixture(params=["socket", "serial"])
def transport(request):
    if request.param == "socket":
        return SocketTransport("test", 8899)
    return SerialTransport("/dev/test", 9600)


async def test_write_notification_precedes_drain_but_follows_byte_write(transport):
    events = []

    async def drain():
        events.append("drain")

    transport._writer = MagicMock(write=lambda data: events.append("write"), drain=drain)
    await transport.write(b"\xaa", on_write=lambda: events.append("notified"))
    assert events == ["write", "notified", "drain"]


async def test_failed_byte_write_does_not_notify(transport):
    transport._writer = MagicMock(
        write=MagicMock(side_effect=OSError("write failed")), drain=AsyncMock()
    )
    observer = MagicMock()
    with pytest.raises(OSError, match="write failed"):
        await transport.write(b"\xaa", on_write=observer)
    observer.assert_not_called()
    transport._writer.drain.assert_not_awaited()

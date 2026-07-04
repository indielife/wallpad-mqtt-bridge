import asyncio
from unittest.mock import AsyncMock

import pytest

from wallpad.transport.bus_arbitration import BusArbitrationTransport


@pytest.fixture
def inner():
    return AsyncMock()


@pytest.fixture
def transport(inner):
    return BusArbitrationTransport(inner, idle_interval=0.1)


async def test_connect_delegates(transport, inner):
    await transport.connect()
    inner.connect.assert_awaited_once()


async def test_close_delegates(transport, inner):
    await transport.close()
    inner.close.assert_awaited_once()


async def test_read_delegates_and_returns_data(transport, inner):
    inner.read.return_value = b"\xaa"

    result = await transport.read(1)

    assert result == b"\xaa"
    inner.read.assert_awaited_once_with(1)


async def test_write_delegates(transport, inner):
    await transport.write(b"\x01\x02")

    inner.write.assert_awaited_once_with(b"\x01\x02")


async def test_is_idle_false_before_interval_elapses(inner):
    transport = BusArbitrationTransport(inner, idle_interval=1.0)
    assert transport.is_idle() is False


async def test_is_idle_true_after_interval_elapses(inner):
    transport = BusArbitrationTransport(inner, idle_interval=0.01)
    await asyncio.sleep(0.05)
    assert transport.is_idle() is True


async def test_is_idle_false_immediately_after_write(transport, inner):
    await transport.write(b"\xaa")

    assert transport.is_idle() is False


async def test_read_updates_activity_even_without_frame_parsing(transport, inner):
    """read()는 프레임 해독 여부와 무관하게 활동으로 기록되어야 한다 — 체크섬이
    유효하지 않거나 해독하지 못한 다른 기기의 트래픽이라도 버스가 바쁘다는
    근거이기 때문이다. 이 계층에는 프레임이라는 개념 자체가 없으므로 이 테스트가
    사실상 버그 수정의 전부다."""
    inner.read.return_value = b"\xff"

    await transport.read(1)

    assert transport.is_idle() is False


async def test_write_if_idle_writes_and_returns_true_when_idle(transport, inner):
    transport._last_activity = 0.0

    result = await transport.write_if_idle(b"\xaa")

    assert result is True
    inner.write.assert_awaited_once_with(b"\xaa")


async def test_write_if_idle_skips_when_busy(transport, inner):
    await transport.write(b"\xaa")

    result = await transport.write_if_idle(b"\xbb")

    assert result is False
    inner.write.assert_awaited_once_with(b"\xaa")


async def test_write_if_idle_serializes_concurrent_writers(transport, inner):
    """스캔 루프와 디버그 에코 경로가 동시에 write_if_idle을 호출해도, 락 안에서
    정숙 여부를 재검사하므로 먼저 끝난 쪽만 실제로 전송되고 나머지는 버스 정숙
    가드에 걸려 스킵된다."""
    transport._last_activity = 0.0
    write_started = asyncio.Event()
    release_write = asyncio.Event()

    async def slow_write(_data):
        write_started.set()
        await release_write.wait()

    inner.write.side_effect = slow_write

    first = asyncio.create_task(transport.write_if_idle(b"\xaa"))
    await write_started.wait()

    second = asyncio.create_task(transport.write_if_idle(b"\xbb"))
    await asyncio.sleep(0)  # second를 락 대기 상태로 진입시킴

    release_write.set()
    first_result, second_result = await asyncio.gather(first, second)

    assert first_result is True
    assert second_result is False
    assert inner.write.await_count == 1

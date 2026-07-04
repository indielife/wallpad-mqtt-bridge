"""RS485 버스 쓰기 단일화(write_to_bus) 및 동시 쓰기 방지 테스트."""

import asyncio
import time
from unittest.mock import AsyncMock

from wallpad.protocol.kocom.constants import KOCOM_INTERVAL


async def test_write_to_bus_writes_and_updates_tick_when_idle(panel_instance):
    panel_instance.transport = AsyncMock()
    panel_instance.tick = 0.0

    result = await panel_instance.write_to_bus("aa5530bc")

    assert result is True
    panel_instance.transport.write.assert_awaited_once()
    assert time.time() - panel_instance.tick < 1


async def test_write_to_bus_skips_when_bus_busy(panel_instance):
    panel_instance.transport = AsyncMock()
    panel_instance.tick = time.time()

    result = await panel_instance.write_to_bus("aa5530bc")

    assert result is False
    panel_instance.transport.write.assert_not_awaited()


async def test_write_to_bus_serializes_concurrent_writers(panel_instance):
    """스캔 루프와 디버그 에코 경로가 동시에 write_to_bus를 호출해도, 락 안에서
    tick을 재검사하므로 먼저 끝난 쪽만 실제로 전송되고 나머지는 버스 정숙
    가드에 걸려 스킵된다."""
    panel_instance.tick = 0.0
    write_started = asyncio.Event()
    release_write = asyncio.Event()

    async def slow_write(_data):
        write_started.set()
        await release_write.wait()

    panel_instance.transport = AsyncMock()
    panel_instance.transport.write.side_effect = slow_write

    first = asyncio.create_task(panel_instance.write_to_bus("aa"))
    await write_started.wait()

    second = asyncio.create_task(panel_instance.write_to_bus("bb"))
    await asyncio.sleep(0)  # second를 락 대기 상태로 진입시킴

    release_write.set()
    first_result, second_result = await asyncio.gather(first, second)

    assert first_result is True
    assert second_result is False
    assert panel_instance.transport.write.await_count == 1


async def test_schedule_write_skips_when_bus_busy(panel_instance, monkeypatch):
    """디버그 패킷 에코(_schedule_write)도 write_to_bus를 경유해 tick 가드를
    존중해야 한다 (이전에는 가드 없이 무조건 전송했음)."""
    panel_instance.transport = AsyncMock()
    panel_instance._loop = asyncio.get_running_loop()
    panel_instance.tick = time.time()

    captured = {}
    monkeypatch.setattr(
        "wallpad.panel.panel.asyncio.run_coroutine_threadsafe",
        lambda coro, loop: captured.setdefault("task", asyncio.ensure_future(coro)),
    )

    panel_instance._schedule_write("aa5530bc")
    await captured["task"]

    panel_instance.transport.write.assert_not_awaited()


async def test_schedule_write_writes_when_bus_idle(panel_instance, monkeypatch):
    panel_instance.transport = AsyncMock()
    panel_instance._loop = asyncio.get_running_loop()
    panel_instance.tick = time.time() - (KOCOM_INTERVAL / 1000) - 1

    captured = {}
    monkeypatch.setattr(
        "wallpad.panel.panel.asyncio.run_coroutine_threadsafe",
        lambda coro, loop: captured.setdefault("task", asyncio.ensure_future(coro)),
    )

    panel_instance._schedule_write("aa5530bc")
    await captured["task"]

    panel_instance.transport.write.assert_awaited_once()

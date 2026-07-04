"""Panel이 StateSynchronizer를 올바르게 소유·기동하는지 검증합니다."""

import asyncio
import time
from unittest.mock import AsyncMock

from wallpad.panel.synchronizer import StateSynchronizer
from wallpad.protocol.kocom.constants import KOCOM_INTERVAL


def test_panel_owns_a_state_synchronizer(panel_instance):
    assert isinstance(panel_instance.synchronizer, StateSynchronizer)
    assert panel_instance.synchronizer.device_states is panel_instance.device_states
    assert panel_instance.synchronizer.send_packet == panel_instance.send_packet
    assert panel_instance.synchronizer.ha_ready is panel_instance.ha_ready


def test_is_bus_idle_reflects_tick_guard(panel_instance):
    now = time.time()
    panel_instance.tick = now
    assert panel_instance.synchronizer.is_bus_idle(now) is False

    panel_instance.tick = now - (KOCOM_INTERVAL / 1000) - 1
    assert panel_instance.synchronizer.is_bus_idle(now) is True


async def test_start_schedules_synchronizer_run(panel_instance):
    panel_instance.transport.connect = AsyncMock()
    run_started = asyncio.Event()

    async def fake_run():
        run_started.set()
        await asyncio.sleep(3600)

    panel_instance.synchronizer.run = fake_run

    tasks = await panel_instance.start()
    await run_started.wait()

    assert panel_instance._task_sync in tasks

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

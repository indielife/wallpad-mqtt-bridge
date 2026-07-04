"""Panel이 StateSynchronizer를 올바르게 소유·기동하는지 검증합니다."""

import asyncio
from unittest.mock import AsyncMock

from wallpad.panel.synchronizer import StateSynchronizer


def test_panel_owns_a_state_synchronizer(panel_instance):
    assert isinstance(panel_instance.synchronizer, StateSynchronizer)
    assert panel_instance.synchronizer.device_states is panel_instance.device_states
    assert panel_instance.synchronizer.send_packet == panel_instance.send_packet
    assert panel_instance.synchronizer.ha_ready is panel_instance.ha_ready


def test_synchronizer_is_bus_idle_wired_to_transport(panel_instance):
    """버스 정숙 판정은 이제 transport(BusArbitrationTransport)가 소유하므로,
    synchronizer에는 그 is_idle을 그대로 주입했는지만 검증한다. 실제 정숙 판정
    로직은 tests/wallpad/transport/test_bus_arbitration.py가 검증한다."""
    assert panel_instance.synchronizer.is_bus_idle is panel_instance.transport.is_idle


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

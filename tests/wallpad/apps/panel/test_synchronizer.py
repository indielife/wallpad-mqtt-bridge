import asyncio
import contextlib
import time
from unittest.mock import AsyncMock, patch

import pytest

from wallpad.apps.panel.send_result import SendResult
from wallpad.apps.panel.state import KocomStateManager
from wallpad.apps.panel.synchronizer import StateSynchronizer
from wallpad.protocol.kocom.constants import DEVICE_ELEVATOR, DEVICE_LIGHT


def _stop_after_one(secs):
    """run()의 0.2초 슬립에서만 루프를 중단합니다."""
    if secs == 0.2:
        raise RuntimeError("stop loop")


@pytest.fixture
def synchronizer(mock_config):
    """gate 열림(HA 준비 완료) 상태의 StateSynchronizer — 버스는 항상 idle로 취급."""
    sync = StateSynchronizer(
        device_states=KocomStateManager(),
        send_packet=AsyncMock(return_value=SendResult.SENT),
        config=mock_config,
        is_bus_idle=lambda: True,
        ha_ready=asyncio.Event(),
    )
    sync.ha_ready.set()
    return sync


async def test_run_blocks_until_ha_ready(mock_config):
    """gate 닫힘(ha_ready 미설정) 상태에서 run()은 블록되어야 한다."""
    sync = StateSynchronizer(
        device_states=KocomStateManager(),
        send_packet=AsyncMock(return_value=SendResult.SENT),
        config=mock_config,
        is_bus_idle=lambda: True,
        ha_ready=asyncio.Event(),
    )

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sync.run(), timeout=0.1)

    sync.send_packet.assert_not_called()


async def test_run_skips_sync_while_bus_busy(mock_config):
    """is_bus_idle이 False를 반환하는 동안은 sync가 수행되지 않아야 한다."""
    sync = StateSynchronizer(
        device_states=KocomStateManager(),
        send_packet=AsyncMock(return_value=SendResult.SENT),
        config=mock_config,
        is_bus_idle=lambda: False,
        ha_ready=asyncio.Event(),
    )
    sync.ha_ready.set()

    with (
        patch("wallpad.apps.panel.synchronizer.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await sync.run()

    sync.send_packet.assert_not_called()


async def test_poll_room_triggers_periodic_query(synchronizer, monkeypatch):
    """poll: 주기적 조회(scan_interval 초과) 기능이 실행되는지 검증합니다."""
    synchronizer.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 100.0, "count": 0, "last": 100.0},
            "light1": {"state": "off", "set": "off", "last": "state", "count": 0},
        }
    }
    scan_state = synchronizer.device_states[DEVICE_LIGHT]["livingroom"].scan
    monkeypatch.setattr(time, "monotonic", lambda: 500.0)

    with (
        patch("wallpad.apps.panel.synchronizer.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await synchronizer.run()

    synchronizer.send_packet.assert_awaited_once_with(
        DEVICE_LIGHT, "livingroom", "", "", cmd="조회"
    )
    assert scan_state.count == 1
    assert scan_state.last == 500.0


async def test_reconcile_device_sends_set_command(synchronizer, monkeypatch):
    """reconcile: 서브 디바이스에 걸린 set 명령을 재전송하는 로직을 검증합니다."""
    synchronizer.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 490.0, "count": 0, "last": 490.0},
            "light1": {"state": "off", "set": "on", "last": "set", "count": 0},
        }
    }
    light1 = synchronizer.device_states[DEVICE_LIGHT]["livingroom"]["light1"]
    monkeypatch.setattr(time, "monotonic", lambda: 500.0)

    with (
        patch("wallpad.apps.panel.synchronizer.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await synchronizer.run()

    synchronizer.send_packet.assert_awaited_once_with(DEVICE_LIGHT, "livingroom", "light1", "on")
    assert light1.last == 500.0


async def test_reconcile_device_retries_after_timeout(synchronizer, monkeypatch):
    """reconcile: 재전송 후 응답 없이 RECONCILE_RETRY_INTERVAL이 지나면 다시 set으로 되돌아가 재시도한다."""
    synchronizer.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 490.0, "count": 0, "last": 490.0},
            "light1": {"state": "off", "set": "off", "last": 498.0, "count": 0},
        }
    }
    light1 = synchronizer.device_states[DEVICE_LIGHT]["livingroom"]["light1"]
    monkeypatch.setattr(time, "monotonic", lambda: 500.0)

    with (
        patch("wallpad.apps.panel.synchronizer.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await synchronizer.run()

    synchronizer.send_packet.assert_not_called()
    assert light1.last == "set"
    assert light1.count == 1


async def test_elevator_skips_poll_and_reconciles_immediately(synchronizer, monkeypatch):
    """엘리베이터는 주기적 poll을 생략하고, 제어 요청(set) 시 즉시 'state'로 복구되는지 검증합니다."""
    synchronizer.device_states[DEVICE_ELEVATOR] = {
        "wallpad": {
            "scan": {"tick": 100.0, "count": 0, "last": 100.0},
            "elevator": {"state": "off", "set": "on", "last": "set", "count": 0},
        }
    }
    scan_state = synchronizer.device_states[DEVICE_ELEVATOR]["wallpad"].scan
    elevator = synchronizer.device_states[DEVICE_ELEVATOR]["wallpad"]["elevator"]
    monkeypatch.setattr(time, "monotonic", lambda: 500.0)

    with (
        patch("wallpad.apps.panel.synchronizer.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await synchronizer.run()

    synchronizer.send_packet.assert_awaited_once_with(DEVICE_ELEVATOR, "wallpad", "elevator", "on")
    assert scan_state.count == 0
    assert elevator.last == "state"


async def test_deferred_send_does_not_start_response_timer(synchronizer):
    from wallpad.apps.panel.send_result import SendResult
    from wallpad.apps.panel.state import SubDeviceState

    state = SubDeviceState(state="off", set_val="on", last="set")
    synchronizer.send_packet.return_value = SendResult.DEFERRED
    await synchronizer.reconcile_device(DEVICE_LIGHT, "livingroom", "light1", state, 100.0)
    assert state.last == "set"
    assert state.count == 0


async def test_poll_counts_only_completed_writes(synchronizer):
    from wallpad.apps.panel.send_result import SendResult
    from wallpad.apps.panel.state import ScanState

    scan = ScanState()
    initial_last = scan.last
    synchronizer.send_packet.return_value = SendResult.DEFERRED
    await synchronizer.poll_room(DEVICE_LIGHT, "livingroom", scan, 500.0)
    assert scan.count == 0
    assert scan.last == initial_last


async def test_busy_bus_still_expires_response_wait(synchronizer, monkeypatch, caplog):
    synchronizer.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 490.0},
            "light1": {"state": "off", "set": "on", "last": 498.0, "count": 4},
        }
    }
    synchronizer.is_bus_idle = lambda: False
    monkeypatch.setattr(time, "monotonic", lambda: 500.0)
    with (
        patch("wallpad.apps.panel.synchronizer.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await synchronizer.run()
    state = synchronizer.device_states[DEVICE_LIGHT]["livingroom"]["light1"]
    assert state.last == "state"
    assert "event=retry_exhausted" in caplog.text
    synchronizer.send_packet.assert_not_called()


async def test_write_completion_starts_timer_and_does_not_overwrite_confirmation(
    synchronizer, monkeypatch
):
    from wallpad.apps.panel.send_result import SendResult
    from wallpad.apps.panel.state import SubDeviceState

    state = SubDeviceState(state="off", set_val="on", last="set")
    monkeypatch.setattr(time, "monotonic", lambda: 510.0)
    synchronizer.send_packet.return_value = SendResult.SENT
    await synchronizer.reconcile_device(DEVICE_LIGHT, "livingroom", "light1", state, 500.0)
    assert state.last == 510.0

    state.last = "set"

    async def send_with_fast_response(*args):
        state.last = "state"
        return SendResult.SENT

    synchronizer.send_packet.side_effect = send_with_fast_response
    await synchronizer.reconcile_device(DEVICE_LIGHT, "livingroom", "light1", state, 500.0)
    assert state.last == "state"


async def test_retry_budget_is_initial_send_plus_four_retries(synchronizer, monkeypatch, caplog):
    from wallpad.apps.panel.state import SubDeviceState

    clock = [500.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    state = SubDeviceState(state="off", set_val="on", last="set")
    for _ in range(5):
        await synchronizer.reconcile_device(DEVICE_LIGHT, "livingroom", "light1", state, clock[0])
        clock[0] += 2.0
        await synchronizer.reconcile_device(DEVICE_LIGHT, "livingroom", "light1", state, clock[0])
    assert synchronizer.send_packet.await_count == 5
    assert state.last == "state"
    assert sum("event=retry_exhausted" in r.message for r in caplog.records) == 1


async def test_failed_write_cannot_cancel_a_replacement_command(synchronizer):
    from wallpad.apps.panel.state import SubDeviceState

    state = SubDeviceState(state="off", set_val="on", last="set")

    async def fail_while_replaced(*args):
        state.set = "off"
        state.last = "set"
        return SendResult.FAILED

    synchronizer.send_packet.side_effect = fail_while_replaced
    await synchronizer.reconcile_device(DEVICE_LIGHT, "livingroom", "light1", state, 500.0)
    assert state.last == "set"

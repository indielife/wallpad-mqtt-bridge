import contextlib
import time
from unittest.mock import AsyncMock, patch

import pytest

from wallpad.panel.panel import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
)
from wallpad.panel.state import KocomStateManager


def _stop_after_one(secs):
    """scan_list의 0.2초 슬립에서만 루프를 중단합니다."""
    if secs == 0.2:
        raise RuntimeError("stop loop")


async def test_scan_list_periodic_scan_trigger(panel_instance, monkeypatch):
    """주기적 스캔(조회) 기능이 실행되는지 검증합니다."""
    # DEVICE_LIGHT만 device_states에 남겨 다른 기기가 스캔에 영향을 주지 않도록 합니다.
    panel_instance.device_states = KocomStateManager()
    panel_instance.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 100.0, "count": 0, "last": 100.0},
            "light1": {"state": "off", "set": "off", "last": "state", "count": 0},
        }
    }

    scan_state = panel_instance.device_states[DEVICE_LIGHT]["livingroom"].scan
    panel_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    panel_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await panel_instance.scan_list()

    panel_instance.set_serial.assert_awaited_once_with(
        DEVICE_LIGHT, "livingroom", "", "", cmd="조회"
    )
    assert scan_state.count == 1
    assert scan_state.last == 500.0


async def test_scan_list_sub_device_set_retry(panel_instance, monkeypatch):
    """서브 디바이스 제어 명령(set)을 전송하는 로직을 검증합니다."""
    panel_instance.device_states = KocomStateManager()
    panel_instance.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 490.0, "count": 0, "last": 490.0},
            "light1": {"state": "off", "set": "on", "last": "set", "count": 0},
        }
    }

    light1 = panel_instance.device_states[DEVICE_LIGHT]["livingroom"]["light1"]

    panel_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    panel_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await panel_instance.scan_list()

    panel_instance.set_serial.assert_awaited_once_with(DEVICE_LIGHT, "livingroom", "light1", "on")
    assert light1.last == 500.0


async def test_scan_list_sub_device_float_retry(panel_instance, monkeypatch):
    """제어 명령 전송 후 1초 동안 응답이 없으면 다시 "set"으로 상태를 되돌리는 재시도 로직을 검증합니다."""
    panel_instance.device_states = KocomStateManager()
    panel_instance.device_states[DEVICE_LIGHT] = {
        "livingroom": {
            "scan": {"tick": 490.0, "count": 0, "last": 490.0},
            "light1": {"state": "off", "set": "off", "last": 498.0, "count": 0},
        }
    }

    light1 = panel_instance.device_states[DEVICE_LIGHT]["livingroom"]["light1"]

    panel_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    panel_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await panel_instance.scan_list()

    panel_instance.set_serial.assert_not_called()
    assert light1.last == "set"
    assert light1.count == 1


async def test_scan_list_elevator_trigger(panel_instance, monkeypatch):
    """엘리베이터가 활성화되었을 때, 주기적 조회를 생략하고 제어 요청(set) 시 즉시 'state'로 복구되는지 검증합니다."""
    panel_instance.device_states = KocomStateManager()
    panel_instance.device_states[DEVICE_ELEVATOR] = {
        "wallpad": {
            "scan": {"tick": 100.0, "count": 0, "last": 100.0},
            "elevator": {"state": "off", "set": "on", "last": "set", "count": 0},
        }
    }

    scan_state = panel_instance.device_states[DEVICE_ELEVATOR]["wallpad"].scan
    elevator = panel_instance.device_states[DEVICE_ELEVATOR]["wallpad"]["elevator"]

    panel_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    panel_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await panel_instance.scan_list()

    panel_instance.set_serial.assert_awaited_once_with(DEVICE_ELEVATOR, "wallpad", "elevator", "on")
    assert scan_state.count == 0
    assert elevator.last == "state"

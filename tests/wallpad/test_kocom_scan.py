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


def _stop_after_one(secs):
    """scan_list의 0.2초 슬립에서만 루프를 중단합니다."""
    if secs == 0.2:
        raise RuntimeError("stop loop")


async def test_scan_list_periodic_scan_trigger(kocom_instance, monkeypatch):
    """주기적 스캔(조회) 기능이 실행되는지 검증합니다."""
    kocom_instance.wp_light = True
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False
    kocom_instance.wp_elevator = False

    scan_state = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"].scan
    scan_state.tick = 100.0
    scan_state.last = 100.0
    scan_state.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await kocom_instance.scan_list()

    kocom_instance.set_serial.assert_awaited_once_with(
        DEVICE_LIGHT, "livingroom", "", "", cmd="조회"
    )
    assert scan_state.count == 1
    assert scan_state.last == 500.0


async def test_scan_list_sub_device_set_retry(kocom_instance, monkeypatch):
    """서브 디바이스 제어 명령(set)을 전송하는 로직을 검증합니다."""
    kocom_instance.wp_light = True
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False
    kocom_instance.wp_elevator = False

    scan_state = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"].scan
    scan_state.tick = 490.0
    scan_state.last = 490.0

    light1 = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]
    light1.last = "set"
    light1.set = "on"
    light1.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await kocom_instance.scan_list()

    kocom_instance.set_serial.assert_awaited_once_with(DEVICE_LIGHT, "livingroom", "light1", "on")
    assert light1.last == 500.0


async def test_scan_list_sub_device_float_retry(kocom_instance, monkeypatch):
    """제어 명령 전송 후 1초 동안 응답이 없으면 다시 "set"으로 상태를 되돌리는 재시도 로직을 검증합니다."""
    kocom_instance.wp_light = True
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False
    kocom_instance.wp_elevator = False

    scan_state = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"].scan
    scan_state.tick = 490.0

    light1 = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]
    light1.last = 498.0
    light1.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await kocom_instance.scan_list()

    kocom_instance.set_serial.assert_not_called()
    assert light1.last == "set"
    assert light1.count == 1


async def test_scan_list_elevator_trigger(kocom_instance, monkeypatch):
    """엘리베이터가 활성화되었을 때, 주기적 조회를 생략하고 제어 요청(set) 시 즉시 'state'로 복구되는지 검증합니다."""
    kocom_instance.wp_elevator = True
    kocom_instance.wp_light = False
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False

    scan_state = kocom_instance.wp_list[DEVICE_ELEVATOR]["wallpad"].scan
    scan_state.tick = 100.0
    scan_state.last = 100.0
    scan_state.count = 0

    elevator = kocom_instance.wp_list[DEVICE_ELEVATOR]["wallpad"]["elevator"]
    elevator.last = "set"
    elevator.set = "on"
    elevator.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = AsyncMock()

    with (
        patch("wallpad.panel.panel.asyncio.sleep", side_effect=_stop_after_one),
        contextlib.suppress(RuntimeError),
    ):
        await kocom_instance.scan_list()

    kocom_instance.set_serial.assert_awaited_once_with(DEVICE_ELEVATOR, "wallpad", "elevator", "on")
    assert scan_state.count == 0
    assert elevator.last == "state"

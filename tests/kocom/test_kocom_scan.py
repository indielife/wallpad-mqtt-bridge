import contextlib
import time
from unittest.mock import MagicMock

import pytest

from kocom.kocom import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
)


def test_scan_list_periodic_scan_trigger(kocom_instance, monkeypatch):
    """주기적 스캔(조회) 기능이 실행되는지 검증합니다."""
    # 기기 활성화 플래그 설정
    kocom_instance.wp_light = True
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False
    kocom_instance.wp_elevator = False

    # scan_interval을 초과하는 상태로 설정
    scan_state = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"].scan
    scan_state.tick = 100.0
    scan_state.last = 100.0
    scan_state.count = 0

    kocom_instance.tick = 400.0  # now (500.0) - tick > 0.1을 만족하도록 설정

    # mock time.time
    monkeypatch.setattr(time, "time", lambda: 500.0)

    # set_serial 모킹
    kocom_instance.set_serial = MagicMock()

    # scan_list의 루프를 1회만 돌고 탈출하도록 StopIteration 예외 발생 모킹
    def mock_sleep(secs):
        if secs == 0.2:
            raise StopIteration

    monkeypatch.setattr(time, "sleep", mock_sleep)

    with contextlib.suppress(StopIteration):
        kocom_instance.scan_list()

    # set_serial이 "조회" 커맨드로 호출되었는지 검증
    kocom_instance.set_serial.assert_called_once_with(
        DEVICE_LIGHT, "livingroom", "", "", cmd="조회"
    )
    assert scan_state.count == 1
    assert scan_state.last == 500.0


def test_scan_list_sub_device_set_retry(kocom_instance, monkeypatch):
    """서브 디바이스 제어 명령(set)을 전송하는 로직을 검증합니다."""
    kocom_instance.wp_light = True
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False
    kocom_instance.wp_elevator = False

    # scan_interval은 초과하지 않은 상태로 만들어서 주기적 조회를 우회
    scan_state = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"].scan
    scan_state.tick = 490.0
    scan_state.last = 490.0

    # sub_device 중 light1의 last를 "set"으로 변경하여 제어 명령 전송을 대기 중인 상태로 설정
    light1 = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]
    light1.last = "set"
    light1.set = "on"
    light1.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = MagicMock()

    def mock_sleep(secs):
        if secs == 0.2:
            raise StopIteration

    monkeypatch.setattr(time, "sleep", mock_sleep)

    with contextlib.suppress(StopIteration):
        kocom_instance.scan_list()

    # set_serial이 light1 제어 명령으로 호출되었는지 검증
    kocom_instance.set_serial.assert_called_once_with(DEVICE_LIGHT, "livingroom", "light1", "on")
    assert light1.last == 500.0


def test_scan_list_sub_device_float_retry(kocom_instance, monkeypatch):
    """제어 명령 전송 후 1초 동안 응답이 없으면 다시 "set"으로 상태를 되돌리는 재시도 로직을 검증합니다."""
    kocom_instance.wp_light = True
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False
    kocom_instance.wp_elevator = False

    scan_state = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"].scan
    scan_state.tick = 490.0

    # light1이 제어 전송 완료(float 시간값 저장) 후 1초 이상 경과한 상태로 설정
    light1 = kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]
    light1.last = 498.0  # 500.0 (현재시간) - 498.0 = 2초 경과 (> 1초)
    light1.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = MagicMock()

    def mock_sleep(secs):
        if secs == 0.2:
            raise StopIteration

    monkeypatch.setattr(time, "sleep", mock_sleep)

    with contextlib.suppress(StopIteration):
        kocom_instance.scan_list()

    # set_serial은 호출되지 않고 (이후 set 루프에서 호출될 것이므로), last만 "set"으로 바뀌고 count가 1 증가해야 함
    kocom_instance.set_serial.assert_not_called()
    assert light1.last == "set"
    assert light1.count == 1


def test_scan_list_elevator_trigger(kocom_instance, monkeypatch):
    """엘리베이터가 활성화되었을 때, 주기적 조회를 생략하고 제어 요청(set) 시 재시도 대기 없이 즉시 'state'로 복구되는지 검증합니다."""
    kocom_instance.wp_elevator = True
    kocom_instance.wp_light = False
    kocom_instance.wp_plug = False
    kocom_instance.wp_thermostat = False
    kocom_instance.wp_fan = False
    kocom_instance.wp_gas = False

    # scan_interval을 초과하는 상태로 설정해서 다른 기기라면 주기적 조회가 발동할 상태로 만듦
    scan_state = kocom_instance.wp_list[DEVICE_ELEVATOR]["wallpad"].scan
    scan_state.tick = 100.0
    scan_state.last = 100.0
    scan_state.count = 0

    # 엘리베이터의 last를 "set"으로 변경하여 호출 명령이 대기 중인 상태로 설정
    elevator = kocom_instance.wp_list[DEVICE_ELEVATOR]["wallpad"]["elevator"]
    elevator.last = "set"
    elevator.set = "on"
    elevator.count = 0

    kocom_instance.tick = 400.0
    monkeypatch.setattr(time, "time", lambda: 500.0)

    kocom_instance.set_serial = MagicMock()

    def mock_sleep(secs):
        if secs == 0.2:
            raise StopIteration

    monkeypatch.setattr(time, "sleep", mock_sleep)

    with contextlib.suppress(StopIteration):
        kocom_instance.scan_list()

    # 엘리베이터는 주기적 "조회" 호출이 이루어지지 않고, 개별 서브 기기 "on" 호출만 발생해야 함
    kocom_instance.set_serial.assert_called_once_with(DEVICE_ELEVATOR, "wallpad", "elevator", "on")

    # 주기적 스캔 count가 증가하지 않았어야 함 (조회가 생략되었으므로)
    assert scan_state.count == 0

    # 엘리베이터 제어 전송 완료 후 last는 float 시간값이나 "set"이 아닌 즉시 "state"로 복구되어야 함 (재시도 방지)
    assert elevator.last == "state"

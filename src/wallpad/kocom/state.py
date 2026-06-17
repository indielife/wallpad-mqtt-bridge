import time
from typing import Any

from wallpad.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
)


class SubDeviceState(dict):
    """서브 기기(조명, 콘센트, 가스밸브 등)의 상태를 저장하는 구조적 객체"""

    def __init__(
        self, state: Any, set_val: Any = None, last: str | float = "state", count: int = 0
    ):
        super().__init__()
        self["state"] = state
        self["set"] = state if set_val is None else set_val
        self["last"] = last
        self["count"] = count

    @property
    def state(self) -> Any:
        return self["state"]

    @state.setter
    def state(self, value: Any) -> None:
        self["state"] = value

    @property
    def set(self) -> Any:
        return self["set"]

    @set.setter
    def set(self, value: Any) -> None:
        self["set"] = value

    @property
    def last(self) -> str | float:
        return self["last"]

    @last.setter
    def last(self, value: str | float) -> None:
        self["last"] = value

    @property
    def count(self) -> int:
        return self["count"]

    @count.setter
    def count(self, value: int) -> None:
        self["count"] = value


class ScanState(dict):
    """각 방/기기 그룹의 주기적 스캔 상태 정보"""

    def __init__(self, tick: float = 0.0, count: int = 0, last: float = 0.0):
        super().__init__()
        self["tick"] = tick
        self["count"] = count
        self["last"] = last

    @property
    def tick(self) -> float:
        return self["tick"]

    @tick.setter
    def tick(self, value: float) -> None:
        self["tick"] = value

    @property
    def count(self) -> int:
        return self["count"]

    @count.setter
    def count(self, value: int) -> None:
        self["count"] = value

    @property
    def last(self) -> float:
        return self["last"]

    @last.setter
    def last(self, value: float) -> None:
        self["last"] = value


class RoomState(dict):
    """방(또는 월패드) 내부의 스캔 상태 및 기기별 상태 컬렉션"""

    def __init__(self, scan: ScanState = None):
        super().__init__()
        self.scan = scan if scan is not None else ScanState()
        self["scan"] = self.scan

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "scan":
            if isinstance(value, dict) and not isinstance(value, ScanState):
                value = ScanState(
                    tick=value.get("tick", 0.0),
                    count=value.get("count", 0),
                    last=value.get("last", 0.0),
                )
            self.scan = value
        else:
            if isinstance(value, dict) and not isinstance(value, SubDeviceState):
                value = SubDeviceState(
                    state=value.get("state"),
                    set_val=value.get("set"),
                    last=value.get("last", "state"),
                    count=value.get("count", 0),
                )
        super().__setitem__(key, value)

    @property
    def sub_devices(self) -> dict[str, SubDeviceState]:
        """scan을 제외한 모든 서브 디바이스들을 반환합니다."""
        return {k: v for k, v in self.items() if k != "scan"}


class DeviceState(dict):
    """장치 종류(Light, Plug 등) 하위의 방(Room) 컬렉션"""

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, dict) and not isinstance(value, RoomState):
            room_state = RoomState()
            for k, v in value.items():
                room_state[k] = v
            value = room_state
        super().__setitem__(key, value)


class KocomStateManager(dict):
    """전체 기기 상태를 총괄 관리하는 최상위 매니저 객체"""

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, dict) and not isinstance(value, DeviceState):
            device_state = DeviceState()
            for k, v in value.items():
                device_state[k] = v
            value = device_state
        super().__setitem__(key, value)

    def update_from_ha(
        self,
        device: str,
        room: str,
        sub_device: str,
        command: str,
        payload: str,
        default_speed: str,
    ) -> None:
        """Home Assistant로부터 수신한 제어 요청을 상태 모델에 반영합니다."""
        r_state = self[device][room]

        if device == DEVICE_GAS:
            sub_state = r_state[sub_device]
            sub_state.set = payload
            sub_state.last = command
        elif device == DEVICE_ELEVATOR:
            sub_state = r_state[sub_device]
            sub_state.set = payload
            if payload == "off":
                sub_state.last = "state"
            else:
                sub_state.last = command
        elif device in (DEVICE_LIGHT, DEVICE_PLUG):
            sub_state = r_state[sub_device]
            sub_state[command] = payload
            sub_state.last = command
        elif device == DEVICE_THERMOSTAT:
            if command != "mode":
                r_state["target_temp"].set = int(float(payload))
                r_state["mode"].set = "heat"
                r_state["target_temp"].last = "set"
                r_state["mode"].last = "set"
            else:
                r_state["mode"].set = payload
                r_state["mode"].last = "set"
        elif device == DEVICE_FAN:
            if command != "mode":
                r_state["speed"].set = payload
                r_state["mode"].set = "on"
            else:
                r_state["speed"].set = default_speed if payload == "on" else "off"
                r_state["mode"].set = payload
            r_state["speed"].last = "set"
            r_state["mode"].last = "set"

    def update_from_rs485(
        self,
        device: str,
        room: str,
        value: Any,
        default_speed: str,
    ) -> None:
        """RS485로부터 수신한 장비 상태 패킷을 상태 모델에 반영하고 스캔을 초기화합니다."""
        r_state = self[device][room]

        # 스캔 타이머 초기화
        r_state.scan.tick = time.time()
        r_state.scan.count = 0
        r_state.scan.last = 0.0

        if device in (DEVICE_GAS, DEVICE_ELEVATOR):
            self._update_gas_elevator_rs485(r_state, device, value)
        elif device == DEVICE_FAN:
            self._update_fan_rs485(r_state, value, default_speed)
        elif device in (DEVICE_LIGHT, DEVICE_PLUG):
            self._update_light_plug_rs485(r_state, value)
        elif device == DEVICE_THERMOSTAT:
            self._update_thermostat_rs485(r_state, value)

    def _update_gas_elevator_rs485(self, r_state: RoomState, device: str, value: Any) -> None:
        sub_state = r_state[device]
        sub_state.state = value
        sub_state.last = "state"
        sub_state.count = 0

    def _update_fan_rs485(self, r_state: RoomState, value: Any, default_speed: str) -> None:
        for sub, v in value.items():
            sub_state = r_state[sub]
            if sub == "mode":
                sub_state.state = v
                r_state["speed"].state = "off" if v == "off" else default_speed
            else:
                sub_state.state = v
                r_state["mode"].state = "off" if v == "off" else "on"

            # 제어가 성공적으로 전달된 경우 복구
            if (
                sub_state.last == "set" or isinstance(sub_state.last, float)
            ) and sub_state.set == sub_state.state:
                sub_state.last = "state"
                sub_state.count = 0

    def _update_light_plug_rs485(self, r_state: RoomState, value: Any) -> None:
        for sub, v in value.items():
            sub_state = r_state[sub]
            sub_state.state = v

            # 제어가 성공적으로 전달된 경우 복구
            if (
                sub_state.last == "set" or isinstance(sub_state.last, float)
            ) and sub_state.set == sub_state.state:
                sub_state.last = "state"
                sub_state.count = 0

    def _update_thermostat_rs485(self, r_state: RoomState, value: Any) -> None:
        for sub, v in value.items():
            sub_state = r_state[sub]
            if sub == "mode":
                sub_state.state = v
            else:
                sub_state.state = int(float(v))
                r_state["mode"].state = "heat"

            # 제어가 성공적으로 전달된 경우 복구
            if (
                sub_state.last == "set" or isinstance(sub_state.last, float)
            ) and sub_state.set == sub_state.state:
                sub_state.last = "state"
                sub_state.count = 0

    def reset_scan_states(self) -> None:
        """장비 구성을 잃지 않고 모든 스캔 타이머를 리셋합니다."""
        for device_state in self.values():
            for room_state in device_state.values():
                room_state.scan.tick = 0.0
                room_state.scan.count = 0
                room_state.scan.last = 0.0

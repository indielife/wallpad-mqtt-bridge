from typing import Any


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

    def __init__(self, scan: ScanState | None = None):
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

    def reset_scan_states(self) -> None:
        """장비 구성을 잃지 않고 모든 스캔 타이머를 리셋합니다."""
        for device_state in self.values():
            for room_state in device_state.values():
                room_state.scan.tick = 0.0
                room_state.scan.count = 0
                room_state.scan.last = 0.0

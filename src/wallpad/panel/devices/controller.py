import time

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.panel.state import RoomState, SubDeviceState


class CategoryController:
    """방(Room) 안에서 한 카테고리(조명·콘센트·온도조절기 등)에 속하는 SubDevice들을
    묶는 컨트롤러입니다.

    RS485의 최소 통신 단위는 (카테고리 x 방)이므로, 이 물리적 제약과 상태 소유는
    leaf(SubDevice)가 아니라 이 컨트롤러에 캡슐화됩니다. 자식들의 상태(`RoomState`)를
    소유하며, HA 제어 반영(`apply_ha_command`)·RS485 수신 반영(`apply_rs485_state`)·
    명령 패킷 조립(`make_packet`)을 모두 자기 상태를 기반으로 수행합니다.

    이 `state`는 `device_states`(synchronizer가 순회하는 인덱스)와 **동일한 객체**로
    연결되어, 컨트롤러의 상태 변이가 곧 `device_states`에 반영됩니다.
    """

    def __init__(
        self,
        category: str,
        room: str,
        state: RoomState | None = None,
        packet_builder: "PacketBuilder | None" = None,
    ):
        self.category = category
        self.room = room
        self.sub_devices: list[BaseDevice] = []
        self.state = state
        self.packet_builder = packet_builder

    def add_sub_device(self, device: BaseDevice) -> None:
        self.sub_devices.append(device)

    def apply_ha_command(
        self, sub_device: str, command: str, payload: str, default_speed: str
    ) -> None:
        """Home Assistant 제어 요청을 자기 RoomState에 반영합니다."""
        raise NotImplementedError

    def apply_rs485_state(self, value, default_speed: str) -> None:
        """RS485 수신 상태를 반영하고 스캔 타이머를 초기화합니다."""
        self.reset_scan()
        self.reflect_rs485(value, default_speed)

    def reflect_rs485(self, value, default_speed: str) -> None:
        """카테고리별 RS485 상태 반영 규칙. 서브클래스가 구현합니다."""
        raise NotImplementedError

    def reset_scan(self) -> None:
        self.state.scan.tick = time.time()
        self.state.scan.count = 0
        self.state.scan.last = 0.0

    def recover_if_confirmed(self, sub_state: SubDeviceState) -> None:
        """제어(set)가 RS485로 확인되면 재전송 대기 상태를 회수합니다."""
        if (
            sub_state.last == "set" or isinstance(sub_state.last, float)
        ) and sub_state.set == sub_state.state:
            sub_state.last = "state"
            sub_state.count = 0

    def make_packet(self, cmd: str, target: str, value: str) -> str | None:
        """카테고리별로 자기 상태를 사용해 패킷을 조립합니다. 서브클래스가 구현합니다."""
        raise NotImplementedError


class SwitchController(CategoryController):
    """조명·콘센트처럼 방 안의 여러 on/off 스위치를 묶는 컨트롤러입니다.

    두 카테고리는 상태 반영 규칙이 동일하므로 이 공통 베이스를 공유합니다.
    """

    def apply_ha_command(
        self, sub_device: str, command: str, payload: str, default_speed: str
    ) -> None:
        sub_state = self.state[sub_device]
        sub_state[command] = payload
        sub_state.last = command

    def reflect_rs485(self, value, default_speed: str) -> None:
        for sub, v in value.items():
            sub_state = self.state[sub]
            sub_state.state = v
            self.recover_if_confirmed(sub_state)

    def make_packet(self, cmd: str, target: str, value: str) -> str | None:
        if target not in self.state:
            return None

        device_type = self.category

        value_hex = ""
        all_device = device_type + "0"
        for i in range(1, 9):
            sub_device = device_type + str(i)
            if target != sub_device:
                if target == all_device:
                    value_hex += "ff" if value == "on" and sub_device in self.state else "00"
                else:
                    if sub_device in self.state and self.state[sub_device].state == "on":
                        value_hex += "ff"
                    else:
                        value_hex += "00"
            else:
                value_hex += "ff" if value == "on" else "00"

        if self.packet_builder:
            return self.packet_builder.encode(
                src=device_type,
                dst="wallpad",
                room=self.room,
                cmd=cmd,
                value_hex=value_hex,
            )
        return None

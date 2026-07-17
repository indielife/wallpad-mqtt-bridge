from wallpad.devices.base import BaseDevice
from wallpad.panel.state import RoomState


class CategoryController:
    """방(Room) 안에서 한 카테고리(조명·콘센트·온도조절기 등)에 속하는 SubDevice들을
    묶는 구조 컨테이너입니다.

    RS485의 최소 통신 단위는 (카테고리 x 방)이므로, 향후 이 물리적 제약과 패킷
    조립 책임은 leaf(SubDevice)가 아니라 이 컨트롤러에 캡슐화됩니다.

    자식 SubDevice들의 상태(`RoomState`)를 소유하는 권위자입니다. 이 `state`는
    `device_states`(synchronizer가 순회하는 인덱스)와 **동일한 객체**로 연결되어,
    컨트롤러의 상태 변이가 곧 `device_states`에 반영됩니다.
    """

    def __init__(self, category: str, room: str, state: RoomState | None = None):
        self.category = category
        self.room = room
        self.sub_devices: list[BaseDevice] = []
        self.state = state

    def add_sub_device(self, device: BaseDevice) -> None:
        self.sub_devices.append(device)

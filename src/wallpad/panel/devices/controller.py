from wallpad.devices.base import BaseDevice


class CategoryController:
    """방(Room) 안에서 한 카테고리(조명·콘센트·온도조절기 등)에 속하는 SubDevice들을
    묶는 구조 컨테이너입니다.

    RS485의 최소 통신 단위는 (카테고리 x 방)이므로, 향후 이 물리적 제약과 패킷
    조립 책임은 leaf(SubDevice)가 아니라 이 컨트롤러에 캡슐화됩니다. 다만 이번
    단계(Composite 1/2)에서는 트리 골격만 세우고 라우팅·상태 소유권은 갖지 않습니다.
    실제 동작 이전은 후속 이슈(#160)에서 다룹니다.
    """

    def __init__(self, category: str, room: str):
        self.category = category
        self.room = room
        self.sub_devices: list[BaseDevice] = []

    def add_sub_device(self, device: BaseDevice) -> None:
        self.sub_devices.append(device)

from wallpad.panel.devices.controller import CategoryController


class Room:
    """기기 계층 트리의 1차 분기점인 방입니다.

    수신 프레임(src_room)·HA 명령(room)이 모두 방을 지목하고, 방은 이미
    RoomConfig로 존재하는 의미 있는 집합체이므로 라우팅의 첫 분기점으로 둡니다.
    전역 카테고리(엘리베이터·가스·팬)는 물리적으로 월패드에 속하므로 "wallpad"
    가상 방이 수용합니다. 이번 단계에서는 CategoryController들을 담는 구조
    컨테이너일 뿐이며, 라우팅 위임은 후속 이슈(#160)에서 다룹니다.
    """

    def __init__(self, name: str):
        self.name = name
        self.controllers: list[CategoryController] = []

    def add_controller(self, controller: CategoryController) -> CategoryController:
        self.controllers.append(controller)
        return controller

    def controller(self, category: str) -> CategoryController | None:
        for controller in self.controllers:
            if controller.category == category:
                return controller
        return None

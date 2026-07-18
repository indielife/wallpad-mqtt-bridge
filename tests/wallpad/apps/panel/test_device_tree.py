"""기기 계층 트리(Room→CategoryController→SubDevice)와 flat 뷰 파생 검증.

(1) DeviceFactory가 config로부터 이 트리를 올바르게 구성하는지, (2) 트리를 평면화한
flat 리스트가 Panel 하위 로직(device_map·command_registry 등)이 기대하는 레거시
순서(카테고리-major)를 그대로 재현하는지를 고정한다.
"""

from unittest.mock import MagicMock

import pytest

from wallpad.apps.panel.devices import CategoryController, Light, Plug, Room
from wallpad.apps.panel.factory import DeviceFactory
from wallpad.apps.panel.panel import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
    flatten_device_tree,
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder


def _make_room(name, room_no=None, light_count=0, plug_count=0, thermo_no=None):
    r = MagicMock()
    r.name = name
    r.room_no = room_no
    r.light_count = light_count
    r.plug_count = plug_count
    r.thermo_no = thermo_no
    r.light_addr = f"{room_no:02d}" if room_no is not None else None
    r.thermo_addr = f"{thermo_no:02d}" if thermo_no is not None else None
    return r


@pytest.fixture
def config():
    cfg = MagicMock()
    cfg.sw_version = "0.1.0"
    cfg.wallpad_manufacturer = "kocom"
    cfg.init_temp = 22
    cfg.kocom_default_speed = "low"
    cfg.elevator_enabled = True
    cfg.gas_enabled = True
    cfg.fan_enabled = True
    cfg.rooms = [
        _make_room("livingroom", room_no=0, light_count=3, plug_count=2, thermo_no=0),
        _make_room("bedroom", room_no=1, light_count=2, plug_count=2, thermo_no=1),
        _make_room("kitchen", room_no=4, light_count=3, plug_count=2),
        _make_room("balcony", room_no=5),  # 활성 기기 없음 → 트리에서 제외되어야 함
    ]
    cfg.kocom_room_rev = {"livingroom": "00", "bedroom": "01", "kitchen": "04", "wallpad": "00"}
    cfg.kocom_room_thermostat_rev = {"livingroom": "00", "bedroom": "01"}
    return cfg


@pytest.fixture
def tree(config):
    builder = KocomPacketBuilder(
        room_rev=config.kocom_room_rev, room_thermostat_rev=config.kocom_room_thermostat_rev
    )
    rooms, _states = DeviceFactory.build(config, config.wallpad_manufacturer, builder)
    return rooms


class TestTreeStructure:
    def test_build_returns_room_tree(self, tree):
        assert all(isinstance(room, Room) for room in tree)

    def test_room_order_is_wallpad_then_config_order(self, tree):
        # 활성 기기가 없는 balcony는 제외된다.
        assert [room.name for room in tree] == [
            DEVICE_WALLPAD,
            "livingroom",
            "bedroom",
            "kitchen",
        ]

    def test_wallpad_room_holds_global_controllers(self, tree):
        wallpad = tree[0]
        assert [c.category for c in wallpad.controllers] == [
            DEVICE_ELEVATOR,
            DEVICE_GAS,
            DEVICE_FAN,
        ]

    def test_room_holds_category_controllers(self, tree):
        livingroom = next(room for room in tree if room.name == "livingroom")
        assert [c.category for c in livingroom.controllers] == [
            DEVICE_LIGHT,
            DEVICE_PLUG,
            DEVICE_THERMOSTAT,
        ]

    def test_controller_lookup_by_category(self, tree):
        livingroom = next(room for room in tree if room.name == "livingroom")
        light_controller = livingroom.controller(DEVICE_LIGHT)
        assert isinstance(light_controller, CategoryController)
        assert livingroom.controller("nonexistent") is None

    def test_light_controller_holds_light_subdevices(self, tree):
        livingroom = next(room for room in tree if room.name == "livingroom")
        lights = livingroom.controller(DEVICE_LIGHT).sub_devices
        assert all(isinstance(d, Light) for d in lights)
        # light0(전체) + light1~3
        assert [d.sub_device for d in lights] == ["light0", "light1", "light2", "light3"]

    def test_kitchen_has_no_thermostat_controller(self, tree):
        kitchen = next(room for room in tree if room.name == "kitchen")
        assert kitchen.controller(DEVICE_THERMOSTAT) is None


class TestStateOwnership:
    """CategoryController가 device_states와 동일한 RoomState 객체를 소유하는지 검증.

    controller.state와 device_states[category][room]이 같은 객체여야, 컨트롤러의
    상태 변이가 synchronizer가 순회하는 device_states에 그대로 반영된다.
    """

    @pytest.fixture
    def built(self, config):
        builder = KocomPacketBuilder(
            room_rev=config.kocom_room_rev, room_thermostat_rev=config.kocom_room_thermostat_rev
        )
        return DeviceFactory.build(config, config.wallpad_manufacturer, builder)

    def test_room_device_controller_shares_state_identity(self, built):
        rooms, states = built
        livingroom = next(room for room in rooms if room.name == "livingroom")
        for category in (DEVICE_LIGHT, DEVICE_PLUG, DEVICE_THERMOSTAT):
            controller = livingroom.controller(category)
            assert controller.state is states[category]["livingroom"]

    def test_global_controller_shares_state_identity(self, built):
        rooms, states = built
        wallpad = rooms[0]
        for category in (DEVICE_ELEVATOR, DEVICE_GAS, DEVICE_FAN):
            controller = wallpad.controller(category)
            assert controller.state is states[category][DEVICE_WALLPAD]


class TestFlatten:
    def test_flatten_reproduces_category_major_order(self, tree):
        flat = flatten_device_tree(tree)
        observed = [(type(d).__name__.lower(), d.room, d.sub_device) for d in flat]

        expected = [
            ("elevator", DEVICE_WALLPAD, "elevator"),
            ("gas", DEVICE_WALLPAD, "gas"),
            ("fan", DEVICE_WALLPAD, "fan"),
            # 조명: 방별로 카테고리-major
            ("light", "livingroom", "light0"),
            ("light", "livingroom", "light1"),
            ("light", "livingroom", "light2"),
            ("light", "livingroom", "light3"),
            ("light", "bedroom", "light0"),
            ("light", "bedroom", "light1"),
            ("light", "bedroom", "light2"),
            ("light", "kitchen", "light0"),
            ("light", "kitchen", "light1"),
            ("light", "kitchen", "light2"),
            ("light", "kitchen", "light3"),
            # 콘센트
            ("plug", "livingroom", "plug0"),
            ("plug", "livingroom", "plug1"),
            ("plug", "livingroom", "plug2"),
            ("plug", "bedroom", "plug0"),
            ("plug", "bedroom", "plug1"),
            ("plug", "bedroom", "plug2"),
            ("plug", "kitchen", "plug0"),
            ("plug", "kitchen", "plug1"),
            ("plug", "kitchen", "plug2"),
            # 온도조절기
            ("thermostat", "livingroom", "thermostat"),
            ("thermostat", "bedroom", "thermostat"),
        ]
        assert observed == expected

    def test_flatten_matches_panel_devices(self, config):
        from wallpad.apps.panel.panel import Panel

        panel = Panel(config, MagicMock(), MagicMock())
        assert panel.devices == flatten_device_tree(panel.rooms)


class TestPlugOnlyRoomOrdering:
    def test_category_major_across_heterogeneous_rooms(self):
        """조명만 있는 방과 콘센트만 있는 방이 섞여도 카테고리-major가 유지되는지."""
        cfg = MagicMock()
        cfg.sw_version = "0.1.0"
        cfg.wallpad_manufacturer = "kocom"
        cfg.init_temp = 22
        cfg.kocom_default_speed = "low"
        cfg.elevator_enabled = False
        cfg.gas_enabled = False
        cfg.fan_enabled = False
        cfg.rooms = [
            _make_room("light_only", room_no=0, light_count=1),
            _make_room("plug_only", room_no=1, plug_count=1),
        ]
        cfg.kocom_room_rev = {"light_only": "00", "plug_only": "01", "wallpad": "00"}
        cfg.kocom_room_thermostat_rev = {}
        builder = KocomPacketBuilder(
            room_rev=cfg.kocom_room_rev, room_thermostat_rev=cfg.kocom_room_thermostat_rev
        )
        rooms, _ = DeviceFactory.build(cfg, cfg.wallpad_manufacturer, builder)
        flat = flatten_device_tree(rooms)

        # 모든 조명이 모든 콘센트보다 앞선다(카테고리-major).
        assert [type(d).__name__ for d in flat] == ["Light", "Light", "Plug", "Plug"]
        assert isinstance(flat[0], Light) and flat[0].room == "light_only"
        assert isinstance(flat[2], Plug) and flat[2].room == "plug_only"

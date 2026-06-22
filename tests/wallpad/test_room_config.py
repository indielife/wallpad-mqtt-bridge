import pytest

from wallpad.config import RoomConfig


class TestRoomConfig:
    def test_light_addr_zero_padded(self):
        assert RoomConfig(name="bedroom", room_no=1).light_addr == "01"

    def test_light_addr_two_digits(self):
        assert RoomConfig(name="room1", room_no=3).light_addr == "03"

    def test_light_addr_none_when_no_room_no(self):
        assert RoomConfig(name="bedroom").light_addr is None

    def test_thermo_addr_zero_padded(self):
        assert RoomConfig(name="bedroom", thermo_no=2).thermo_addr == "02"

    def test_thermo_addr_none_when_omitted(self):
        assert RoomConfig(name="kitchen", room_no=4).thermo_addr is None

    def test_different_room_no_and_thermo_no(self):
        """물리적으로 같은 방이지만 조명/난방 패킷 주소가 다른 경우를 검증합니다."""
        room = RoomConfig(name="room1", room_no=3, thermo_no=2)
        assert room.light_addr == "03"
        assert room.thermo_addr == "02"

    def test_defaults(self):
        room = RoomConfig(name="kitchen", room_no=4)
        assert room.light_count == 0
        assert room.plug_count == 0
        assert room.thermo_no is None

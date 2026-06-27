from unittest.mock import MagicMock

import pytest

from wallpad.panel.panel import WallpadPanel


def _make_room(name, room_no=None, light_count=0, plug_count=0, thermo_no=None):
    """테스트용 RoomConfig MagicMock을 생성합니다."""
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
def mock_config():
    """테스트용 설정 모킹"""
    config = MagicMock()
    config.sw_version = "0.1.0"
    config.wallpad_manufacturer = "kocom"

    # Advanced 세부 제어 설정
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.kocom_default_speed = "low"

    # 방 기반 기기: rooms 리스트
    config.rooms = [
        _make_room("livingroom", room_no=0, light_count=3, plug_count=2, thermo_no=0),
    ]

    # 집 전체 단위 기기 활성화
    config.fan_enabled = True
    config.gas_enabled = True
    config.elevator_enabled = True

    # 패킷 빌딩/파싱용 파생 매핑
    config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "wallpad": "00",
    }
    config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
    }
    config.kocom_room = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_room_thermostat = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_light_size = {"livingroom": 3}
    config.kocom_plug_size = {"livingroom": 2}

    return config


@pytest.fixture
def panel_gated(mock_config):
    """gate 닫힘(초기화 미완료) 상태의 패널 — kocom_scan=True(기본값)."""
    return WallpadPanel(mock_config, MagicMock(), MagicMock())


@pytest.fixture
def panel_instance(mock_config):
    """gate 열림(HA 준비 완료) 상태의 패널 — kocom_scan=False."""
    panel = WallpadPanel(mock_config, MagicMock(), MagicMock())
    panel.kocom_scan = False
    return panel

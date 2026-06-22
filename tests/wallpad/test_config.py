import json
import os
from unittest.mock import mock_open, patch

import pytest

from wallpad.config import AppConfig, RoomConfig

SAMPLE_OPTIONS_JSON = {
    "mqtt_broker": {
        "host": "192.168.1.200",
        "username": "test_user",
        "password": "test_password",
    },
    "wallpad": {
        "enable": True,
        "manufacturer": "kocom",
        "connection_type": "Serial",
        "socket": {"host": "192.168.1.100", "port": 8899},
        "serial": {"port": "/dev/ttyUSB0"},
        "enabled_devices": {
            "fan": False,
            "gas": True,
            "elevator": False,
        },
    },
    "rooms": [
        {"name": "livingroom", "room_no": 0, "light_count": 3, "plug_count": 2, "thermo_no": 0},
        {"name": "bedroom", "room_no": 1, "light_count": 2, "plug_count": 2, "thermo_no": 1},
    ],
    "advanced": {
        "init_temp": 24,
        "scan_interval": 500,
        "packet_delay": 1.5,
        "default_speed": "high",
        "loglevel": "debug",
    },
    "ventilator": {
        "enable": False,
        "manufacturer": "grex",
        "connection_type": "Serial",
        "serial": {"ventilator_port": "/dev/ttyUSB1", "controller_port": "/dev/ttyUSB2"},
        "socket": {"host": "192.168.1.101", "port": 8899},
        "default_speed": "low",
    },
}


@patch.dict(
    os.environ, {"MQTT_HOST": "", "MQTT_USERNAME": "", "MQTT_PASSWORD": "", "WALLPAD_HOST": ""}
)
@patch("wallpad.config.os.path.isfile", return_value=True)
def test_app_config_load(mock_isfile):
    """AppConfig가 options.json을 읽고 각 변수에 올바르게 매핑하는지 검증합니다."""
    mock_file = mock_open(read_data=json.dumps(SAMPLE_OPTIONS_JSON))
    with patch("builtins.open", mock_file):
        config = AppConfig(options_path="/fake/path.json")
        config.load()

        # 1. MQTT 설정 검증
        assert config.mqtt_config.host == "192.168.1.200"
        assert config.wallpad_enabled is True
        assert config.wallpad == "kocom"
        assert config.wallpad_manufacturer == "kocom"

        # 2. 통신 타입 및 소켓 설정 검증
        assert config.comm_type == "serial"
        assert config.socket_host == "192.168.1.100"
        assert config.socket_port == 8899

        # 3. 시리얼 포트 설정 검증
        assert config.serial_port == "/dev/ttyUSB0"

        # 4. 집 전체 단위 기기 (fan/gas/elevator) 검증
        assert config.wp_gas is True
        assert config.wp_fan is False
        assert config.wp_elevator is False

        # 5. Advanced 설정 검증
        assert config.init_temp == 24
        assert config.scan_interval == 500
        assert config.packey_delay == 1.5
        assert config.kocom_default_speed == "high"
        assert config.log_level == "debug"

        # 6. rooms 파싱 검증
        assert len(config.rooms) == 2
        assert config.rooms[0].name == "livingroom"
        assert config.rooms[0].light_addr == "00"
        assert config.rooms[0].thermo_addr == "00"
        assert config.rooms[0].light_count == 3
        assert config.rooms[1].name == "bedroom"
        assert config.rooms[1].light_addr == "01"
        assert config.rooms[1].thermo_addr == "01"

        # 7. 파생 매핑 검증
        assert config.kocom_room == {"00": "livingroom", "01": "bedroom"}
        assert config.kocom_room_thermostat == {"00": "livingroom", "01": "bedroom"}
        assert config.kocom_light_size == {"livingroom": 3, "bedroom": 2}
        assert config.kocom_plug_size == {"livingroom": 2, "bedroom": 2}

        # 8. 전열교환기(Ventilator) 설정 파싱 검증
        assert config.ventilator_enabled is False
        assert config.ventilator == "grex"
        assert config.ventilator_manufacturer == "grex"
        assert config.ventilator_connection_type == "serial"
        assert config.ventilator_unit_port == "/dev/ttyUSB1"
        assert config.ventilator_ctrl_port == "/dev/ttyUSB2"
        assert config.ventilator_socket_host == "192.168.1.101"
        assert config.ventilator_socket_port == 8899
        assert config.ventilator_default_speed == "low"


@patch("wallpad.config.os.path.isfile", return_value=False)
def test_app_config_defaults(mock_isfile):
    """options.json 파일이 없을 때 기본 rooms 및 파생 매핑이 올바르게 설정되는지 검증합니다."""
    config = AppConfig(options_path="/fake/nonexistent.json")
    config.load()

    # 집 전체 단위 기기는 기본 비활성화
    assert config.wp_fan is False
    assert config.wp_gas is False
    assert config.wp_elevator is False
    assert config.wallpad_enabled is True
    assert config.wallpad == "kocom"
    assert config.kocom_default_speed == "low"
    assert config.ventilator_enabled is False
    assert config.ventilator == "none"
    assert config.ventilator_default_speed == "low"

    # 1. 기본 방 정보 파생 매핑 검증
    assert config.kocom_room == {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room2",
        "03": "room1",
        "04": "kitchen",
    }
    assert config.kocom_room_thermostat == {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room1",
        "03": "room2",
    }

    # 2. 기본 역방향 맵핑 검증
    assert config.kocom_room_rev == {
        "livingroom": "00",
        "bedroom": "01",
        "room2": "02",
        "room1": "03",
        "kitchen": "04",
        "wallpad": "00",
    }
    assert config.kocom_room_thermostat_rev == {
        "livingroom": "00",
        "bedroom": "01",
        "room1": "02",
        "room2": "03",
    }

    # 3. 기본 기기 개수 검증
    assert config.kocom_light_size == {
        "livingroom": 3,
        "bedroom": 2,
        "room1": 2,
        "room2": 2,
        "kitchen": 3,
    }
    assert config.kocom_plug_size == {
        "livingroom": 2,
        "bedroom": 2,
        "room1": 2,
        "room2": 2,
        "kitchen": 2,
    }


@patch.dict(
    os.environ,
    {
        "MQTT_HOST": "10.0.0.99",
        "MQTT_USERNAME": "envuser",
        "MQTT_PASSWORD": "envpass",
        "WALLPAD_HOST": "10.0.0.50",
    },
)
@patch("wallpad.config.os.path.isfile", return_value=True)
def test_env_var_overrides_options_json(mock_isfile):
    """환경변수가 options.json 값보다 우선 적용되는지 검증합니다."""
    mock_file = mock_open(read_data=json.dumps(SAMPLE_OPTIONS_JSON))
    with patch("builtins.open", mock_file):
        config = AppConfig(options_path="/fake/path.json")
        config.load()

        assert config.mqtt_config.host == "10.0.0.99"
        assert config.mqtt_config.username == "envuser"
        assert config.mqtt_config.password == "envpass"
        assert config.socket_host == "10.0.0.50"


# --- AppConfig.validate() 테스트 ---


def _make_config(**kwargs) -> AppConfig:
    """테스트용 AppConfig를 직접 속성 설정으로 생성합니다."""
    config = AppConfig.__new__(AppConfig)
    AppConfig.__init__(config)
    for key, value in kwargs.items():
        setattr(config, key, value)
    return config


class TestValidateWallpad:
    def test_serial_ok(self):
        config = _make_config(comm_type="serial", serial_port="/dev/ttyUSB0")
        config.validate()

    def test_serial_missing_port(self):
        config = _make_config(comm_type="serial", serial_port="")
        with pytest.raises(ValueError, match=r"Wallpad serial port is not configured\."):
            config.validate()

    def test_socket_ok(self):
        config = _make_config(comm_type="socket", socket_host="192.168.1.100")
        config.validate()

    def test_socket_missing_host(self):
        config = _make_config(comm_type="socket", socket_host=None)
        with pytest.raises(ValueError, match=r"Wallpad socket host is not configured\."):
            config.validate()


class TestValidateVentilator:
    def test_disabled_skips_validation(self):
        config = _make_config(
            comm_type="serial",
            serial_port="/dev/ttyUSB0",
            ventilator_connection_type="serial",
            ventilator_ctrl_port="",
            ventilator_unit_port="",
        )
        config._ventilator_enabled = False
        config.validate()

    def test_serial_ok(self):
        config = _make_config(
            comm_type="serial",
            serial_port="/dev/ttyUSB0",
            ventilator_connection_type="serial",
            ventilator_ctrl_port="/dev/ttyUSB1",
            ventilator_unit_port="/dev/ttyUSB2",
        )
        config._ventilator_enabled = True
        config.validate()

    def test_serial_missing_ctrl_port(self):
        config = _make_config(
            comm_type="serial",
            serial_port="/dev/ttyUSB0",
            ventilator_connection_type="serial",
            ventilator_ctrl_port="",
            ventilator_unit_port="/dev/ttyUSB2",
        )
        config._ventilator_enabled = True
        with pytest.raises(ValueError, match=r"Ventilator serial ports are not fully configured\."):
            config.validate()

    def test_serial_missing_unit_port(self):
        config = _make_config(
            comm_type="serial",
            serial_port="/dev/ttyUSB0",
            ventilator_connection_type="serial",
            ventilator_ctrl_port="/dev/ttyUSB1",
            ventilator_unit_port="",
        )
        config._ventilator_enabled = True
        with pytest.raises(ValueError, match=r"Ventilator serial ports are not fully configured\."):
            config.validate()

    def test_socket_not_supported(self):
        config = _make_config(
            comm_type="serial",
            serial_port="/dev/ttyUSB0",
            ventilator_connection_type="socket",
            ventilator_socket_host="192.168.1.101",
        )
        config._ventilator_enabled = True
        with pytest.raises(
            ValueError, match=r"Ventilator socket connection is not yet supported\."
        ):
            config.validate()

    def test_socket_missing_host_not_supported(self):
        config = _make_config(
            comm_type="serial",
            serial_port="/dev/ttyUSB0",
            ventilator_connection_type="socket",
            ventilator_socket_host="",
        )
        config._ventilator_enabled = True
        with pytest.raises(
            ValueError, match=r"Ventilator socket connection is not yet supported\."
        ):
            config.validate()


# --- 새 rooms 포맷 파싱 테스트 ---

SAMPLE_OPTIONS_JSON_ROOMS = {
    "mqtt_broker": {
        "host": "192.168.1.200",
        "username": "test_user",
        "password": "test_password",
    },
    "wallpad": {
        "enable": True,
        "manufacturer": "kocom",
        "connection_type": "Serial",
        "socket": {"host": "192.168.1.100", "port": 8899},
        "serial": {"port": "/dev/ttyUSB0"},
        "enabled_devices": {
            "fan": False,
            "gas": True,
            "elevator": False,
        },
    },
    "rooms": [
        {"name": "livingroom", "room_no": 0, "light_count": 3, "plug_count": 2, "thermo_no": 0},
        {"name": "bedroom", "room_no": 1, "light_count": 2, "plug_count": 2, "thermo_no": 1},
        # room1은 조명 주소 03, 난방 주소 02로 교차하는 실제 케이스
        {"name": "room1", "room_no": 3, "light_count": 2, "plug_count": 2, "thermo_no": 2},
        {"name": "kitchen", "room_no": 4, "light_count": 3, "plug_count": 2},
    ],
    "advanced": {
        "init_temp": 22,
        "scan_interval": 300,
        "packet_delay": 0.8,
        "default_speed": "low",
        "loglevel": "info",
    },
    "ventilator": {
        "enable": False,
        "manufacturer": "none",
        "connection_type": "Serial",
        "serial": {"ventilator_port": "", "controller_port": ""},
        "socket": {"host": "", "port": 8899},
    },
}


@patch.dict(
    os.environ, {"MQTT_HOST": "", "MQTT_USERNAME": "", "MQTT_PASSWORD": "", "WALLPAD_HOST": ""}
)
@patch("wallpad.config.os.path.isfile", return_value=True)
def test_app_config_load_rooms(mock_isfile):
    """새 rooms 포맷 options.json을 읽고 RoomConfig 리스트로 올바르게 파싱하는지 검증합니다."""
    mock_file = mock_open(read_data=json.dumps(SAMPLE_OPTIONS_JSON_ROOMS))
    with patch("builtins.open", mock_file):
        config = AppConfig(options_path="/fake/path.json")
        config.load()

        assert len(config.rooms) == 4

        livingroom = config.rooms[0]
        assert livingroom.name == "livingroom"
        assert livingroom.light_addr == "00"
        assert livingroom.thermo_addr == "00"
        assert livingroom.light_count == 3
        assert livingroom.plug_count == 2

        # 조명/난방 패킷 주소가 다른 방
        room1 = config.rooms[2]
        assert room1.name == "room1"
        assert room1.light_addr == "03"
        assert room1.thermo_addr == "02"

        # 난방이 없는 방
        kitchen = config.rooms[3]
        assert kitchen.name == "kitchen"
        assert kitchen.light_addr == "04"
        assert kitchen.thermo_addr is None

        # 역방향 매핑 검증 (패킷 빌딩에 사용)
        assert config.kocom_room_rev == {
            "livingroom": "00",
            "bedroom": "01",
            "room1": "03",
            "kitchen": "04",
            "wallpad": "00",
        }
        assert config.kocom_room_thermostat_rev == {
            "livingroom": "00",
            "bedroom": "01",
            "room1": "02",
        }

        # fan/gas/elevator는 여전히 enabled_devices boolean
        assert config.wp_fan is False
        assert config.wp_gas is True
        assert config.wp_elevator is False


@patch("wallpad.config.os.path.isfile", return_value=False)
def test_app_config_default_rooms(mock_isfile):
    """options.json 없을 때 기본 rooms 리스트가 올바르게 설정되는지 검증합니다."""
    config = AppConfig(options_path="/fake/nonexistent.json")
    config.load()

    assert len(config.rooms) > 0

    names = [r.name for r in config.rooms]
    assert "livingroom" in names
    assert "kitchen" in names

    for room in config.rooms:
        assert isinstance(room, RoomConfig)
        assert room.name
        assert room.light_addr is not None

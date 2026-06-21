import json
import os
from unittest.mock import mock_open, patch

import pytest

from wallpad.config import AppConfig

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
            "light": True,
            "plug": False,
            "thermostat": True,
            "fan": False,
            "gas": True,
            "elevator": False,
        },
    },
    "advanced": {
        "init_temp": 24,
        "scan_interval": 500,
        "packet_delay": 1.5,
        "default_speed": "high",
        "loglevel": "debug",
    },
    "kocom_light_size": [{"name": "livingroom", "number": 3}, {"name": "bedroom", "number": 2}],
    "kocom_plug_size": [{"name": "livingroom", "number": 2}],
    "kocom_room": ["livingroom", "bedroom"],
    "kocom_room_thermostat": ["livingroom"],
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

        # 1. MQTT 및 기기 활성화 설정 (Enabled Devices, Boolean 타입 정상 파싱) 검증
        assert config.mqtt_config.host == "192.168.1.200"
        assert config.wallpad_enabled is True
        assert config.wallpad == "kocom"
        assert config.wallpad_manufacturer == "kocom"
        assert config.wp_list["light"] is True
        assert config.wp_list["plug"] is False
        assert config.wp_list["gas"] is True
        assert config.wp_list["fan"] is False

        # 2. 통신 타입 및 소켓 설정 검증
        assert config.comm_type == "serial"
        assert config.socket_host == "192.168.1.100"
        assert config.socket_port == 8899

        # 3. 시리얼 포트 설정 검증
        assert config.serial_port == "/dev/ttyUSB0"

        # 4. 개별 디바이스 헬퍼 프로퍼티 검증
        assert config.wp_light is True
        assert config.wp_plug is False
        assert config.wp_gas is True
        assert config.wp_fan is False
        assert config.wp_thermostat is True
        assert config.wp_elevator is False

        # 5. Advanced 설정 검증
        assert config.init_temp == 24
        assert config.scan_interval == 500
        assert config.packey_delay == 1.5
        assert config.kocom_default_speed == "high"
        assert config.log_level == "debug"

        # 6. 딕셔너리 리스트 (방, 조명, 플러그) 검증
        assert config.kocom_light_size == {"livingroom": 3, "bedroom": 2}
        assert config.kocom_plug_size == {"livingroom": 2}
        assert config.kocom_room == {"00": "livingroom", "01": "bedroom"}
        assert config.kocom_room_thermostat == {"00": "livingroom"}

        # 7. 신규 전열교환기(Ventilator) 설정 파싱 검증
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
    """options.json 파일이 없을 때 기본 방 설정 및 역방향 맵핑 프로퍼티가 올바르게 로드되는지 검증합니다."""
    config = AppConfig(options_path="/fake/nonexistent.json")
    config.load()

    # 기본 디바이스 활성화 상태는 False인지 검증
    assert config.wp_light is False
    assert config.wp_fan is False
    assert config.wp_thermostat is False
    assert config.wp_plug is False
    assert config.wp_gas is False
    assert config.wp_elevator is False
    assert config.wallpad_enabled is True
    assert config.wallpad == "kocom"
    assert config.kocom_default_speed == "low"
    assert config.ventilator_enabled is False
    assert config.ventilator == "none"
    assert config.ventilator_default_speed == "low"

    # 1. 기본 방 정보 검증
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

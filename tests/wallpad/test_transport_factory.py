import json
from unittest.mock import MagicMock, patch

import pytest

from wallpad.config import AppConfig
from wallpad.transport import (
    create_ventilator_adapters,
    create_wallpad_adapter,
)
from wallpad.transport.serial import SerialAdapter
from wallpad.transport.socket import SocketAdapter

SERIAL_OPTIONS_JSON = {
    "mqtt_broker": {
        "host": "192.168.1.50",
        "username": "my_user",
        "password": "my_pass",
    },
    "wallpad": {
        "enable": True,
        "connection_type": "Serial",
        "serial": {"port": "/dev/ttyUSB0"},
        "enabled_devices": {
            "light": True,
            "fan": False,
            "thermostat": True,
            "plug": False,
            "gas": True,
            "elevator": False,
        },
    },
    "ventilator": {
        "enable": True,
        "manufacturer": "Grex",
        "connection_type": "Serial",
        "serial": {"ventilator_port": "/dev/ttyUSB1", "controller_port": "/dev/ttyUSB2"},
    },
}

SOCKET_OPTIONS_JSON = {
    "mqtt_broker": {
        "host": "192.168.1.100",
    },
    "wallpad": {
        "enable": True,
        "connection_type": "Socket",
        "socket": {"host": "192.168.1.200", "port": 8899},
        "enabled_devices": {
            "light": False,
            "fan": True,
            "thermostat": False,
            "plug": True,
            "gas": False,
            "elevator": True,
        },
    },
}


@pytest.fixture
def mock_serial():
    with patch("wallpad.transport.serial.serial.Serial") as mock:
        mock_instance = MagicMock()
        mock_instance.isOpen.return_value = True
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_socket():
    with patch("wallpad.transport.socket.socket") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


def test_create_wallpad_adapter_serial(tmp_path, mock_serial):
    """create_wallpad_adapter가 Serial 포트 설정을 바탕으로 SerialAdapter를 생성하는지 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SERIAL_OPTIONS_JSON))

    config = AppConfig(options_path=str(options_file))
    config.load()

    adapter = create_wallpad_adapter(config)
    assert isinstance(adapter, SerialAdapter)
    assert config.serial_port == "/dev/ttyUSB0"


def test_create_wallpad_adapter_socket(tmp_path, mock_socket):
    """create_wallpad_adapter가 Socket 설정을 바탕으로 SocketAdapter를 생성하는지 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SOCKET_OPTIONS_JSON))

    config = AppConfig(options_path=str(options_file))
    config.load()

    adapter = create_wallpad_adapter(config)
    assert isinstance(adapter, SocketAdapter)


def test_create_ventilator_adapters_serial(tmp_path, mock_serial):
    """create_ventilator_adapters가 Serial 설정을 바탕으로 두 개의 SerialAdapter를 생성하는지 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SERIAL_OPTIONS_JSON))

    config = AppConfig(options_path=str(options_file))
    config.load()

    ctrl, unit = create_ventilator_adapters(config)
    assert isinstance(ctrl, SerialAdapter)
    assert isinstance(unit, SerialAdapter)
    assert config.ventilator_ctrl_port == "/dev/ttyUSB2"
    assert config.ventilator_unit_port == "/dev/ttyUSB1"


def test_create_wallpad_adapter_invalid_type(tmp_path):
    """잘못된 wallpad 연결 타입 설정 시 ValueError를 발생하는지 검증합니다."""
    invalid_options = SOCKET_OPTIONS_JSON.copy()
    invalid_options["wallpad"] = invalid_options["wallpad"].copy()
    invalid_options["wallpad"]["connection_type"] = "unknown"

    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(invalid_options))

    config = AppConfig(options_path=str(options_file))
    config.load()

    with pytest.raises(ValueError, match="Invalid Wallpad connection type: unknown"):
        create_wallpad_adapter(config)

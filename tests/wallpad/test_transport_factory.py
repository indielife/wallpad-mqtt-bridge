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
    "RS485": {"type": "Serial"},
    "Serial": {"Port": "/dev/ttyUSB0"},
    "SerialDevice": {"port1": "kocom"},
    "Ventilator": {
        "enable": True,
        "Manufacturer": "Grex",
        "Connection Type": "Serial",
        "Serial": {"Ventilator Port": "/dev/ttyUSB1", "Controller Port": "/dev/ttyUSB2"},
    },
    "MQTT": {
        "anonymous": False,
        "server": "192.168.1.50",
        "username": "my_user",
        "password": "my_pass",
    },
    "Wallpad": {
        "enable": True,
        "Connection Type": "Serial",
        "light": True,
        "fan": False,
        "thermostat": True,
        "plug": False,
        "gas": True,
        "elevator": False,
    },
}

SOCKET_OPTIONS_JSON = {
    "RS485": {"type": "Socket"},
    "Socket": {"Server": "192.168.1.200", "Port": 8899},
    "SocketDevice": {"device": "kocom"},
    "MQTT": {
        "anonymous": True,
        "server": "192.168.1.100",
    },
    "Wallpad": {
        "enable": True,
        "Connection Type": "Socket",
        "light": False,
        "fan": True,
        "thermostat": False,
        "plug": True,
        "gas": False,
        "elevator": True,
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
    invalid_options["Wallpad"] = invalid_options["Wallpad"].copy()
    invalid_options["Wallpad"]["Connection Type"] = "unknown"

    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(invalid_options))

    config = AppConfig(options_path=str(options_file))
    config.load()

    with pytest.raises(ValueError, match="Invalid Wallpad connection type: unknown"):
        create_wallpad_adapter(config)

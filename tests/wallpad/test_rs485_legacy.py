import json
from unittest.mock import MagicMock, patch

import pytest

from wallpad.config import AppConfig
from wallpad.rs485 import RS485

SERIAL_OPTIONS_JSON = {
    "RS485": {"type": "Serial"},
    "Serial": {"port1": "/dev/ttyUSB0", "port2": "/dev/ttyUSB1"},
    "SerialDevice": {"port1": "kocom", "port2": "grex_ventilator"},
    "MQTT": {
        "anonymous": False,
        "server": "192.168.1.50",
        "username": "my_user",
        "password": "my_pass",
    },
    "Wallpad": {
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
    "Socket": {"server": "192.168.1.200", "port": 8899},
    "SocketDevice": {"device": "kocom"},
    "MQTT": {
        "anonymous": True,
        "server": "192.168.1.100",
    },
    "Wallpad": {
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
    with patch("wallpad.rs485.rs485.serial.Serial") as mock:
        mock_instance = MagicMock()
        mock_instance.isOpen.return_value = True
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_socket():
    with patch("wallpad.rs485.rs485.socket.socket") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


def test_legacy_rs485_serial(tmp_path, mock_serial):
    """rs485.conf 대신 AppConfig를 사용하여 serial 타입 설정을 파싱하는 동작을 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SERIAL_OPTIONS_JSON))

    config = AppConfig(options_path=str(options_file))
    config.load()

    rs485 = RS485(config)

    # 1. Serial 포트 및 디바이스 파싱 검증
    assert rs485.type == "serial"
    assert len(rs485._port_url) == 2
    assert rs485._port_url[1] == "/dev/ttyUSB0"
    assert rs485._port_url[2] == "/dev/ttyUSB1"


def test_legacy_rs485_socket(tmp_path, mock_socket):
    """rs485.conf 대신 AppConfig를 사용하여 socket 타입 설정을 파싱하는 동작을 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SOCKET_OPTIONS_JSON))

    config = AppConfig(options_path=str(options_file))
    config.load()

    rs485 = RS485(config)

    # 1. Socket 설정 파싱 검증
    assert rs485.type == "socket"

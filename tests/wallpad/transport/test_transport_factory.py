import json

from wallpad.config import AppConfig
from wallpad.transport import (
    create_ventilator_transports,
    create_wallpad_transport,
)
from wallpad.transport.reconnect import ReconnectingTransport
from wallpad.transport.serial import SerialTransport
from wallpad.transport.socket import SocketTransport

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
        "manufacturer": "grex",
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


def test_create_wallpad_transport_serial(tmp_path):
    """Serial 설정 시 ReconnectingTransport(SerialTransport)를 반환하는지 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SERIAL_OPTIONS_JSON))
    config = AppConfig(options_path=str(options_file))
    config.load()

    transport = create_wallpad_transport(config)

    assert isinstance(transport, ReconnectingTransport)
    assert isinstance(transport._transport, SerialTransport)
    assert transport._transport.port == "/dev/ttyUSB0"


def test_create_wallpad_transport_socket(tmp_path, monkeypatch):
    """Socket 설정 시 ReconnectingTransport(SocketTransport)를 반환하는지 검증합니다."""
    monkeypatch.delenv("WALLPAD_HOST", raising=False)
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SOCKET_OPTIONS_JSON))
    config = AppConfig(options_path=str(options_file))
    config.load()

    transport = create_wallpad_transport(config)

    assert isinstance(transport, ReconnectingTransport)
    assert isinstance(transport._transport, SocketTransport)
    assert transport._transport.host == "192.168.1.200"
    assert transport._transport.port == 8899


def test_create_ventilator_transports_serial(tmp_path):
    """Serial 설정 시 두 개의 ReconnectingTransport(SerialTransport)를 반환하는지 검증합니다."""
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps(SERIAL_OPTIONS_JSON))
    config = AppConfig(options_path=str(options_file))
    config.load()

    ctrl, unit = create_ventilator_transports(config)

    assert isinstance(ctrl, ReconnectingTransport)
    assert isinstance(ctrl._transport, SerialTransport)
    assert ctrl._transport.port == "/dev/ttyUSB2"

    assert isinstance(unit, ReconnectingTransport)
    assert isinstance(unit._transport, SerialTransport)
    assert unit._transport.port == "/dev/ttyUSB1"



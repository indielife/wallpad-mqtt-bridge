import os
from unittest.mock import MagicMock, patch

import pytest

from kocom.rs485 import RS485

LEGACY_SERIAL_CONF = """[RS485]
type = serial

[Wallpad]
light = True
fan = False
thermostat = True
plug = False
gas = True
elevator = False

[MQTT]
server = 192.168.1.50
anonymous = False
username = my_user
password = my_pass

[Serial]
port1 = /dev/ttyUSB0
port2 = /dev/ttyUSB1
port3 =

[SerialDevice]
port1 = kocom
port2 = grex_ventilator
port3 =
"""

LEGACY_SOCKET_CONF = """[RS485]
type = socket

[Wallpad]
light = False
fan = True
thermostat = False
plug = True
gas = False
elevator = True

[MQTT]
server = 192.168.1.100
anonymous = True

[Socket]
server = 192.168.1.200
port = 8899

[SocketDevice]
device = kocom
"""


@pytest.fixture
def mock_serial():
    with patch("kocom.rs485.serial.Serial") as mock:
        # mock serial instance behavior
        mock_instance = MagicMock()
        mock_instance.isOpen.return_value = True
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_socket():
    with patch("kocom.rs485.socket.socket") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


def test_legacy_rs485_serial(tmp_path, mock_serial):
    """rs485.conf의 type이 serial인 경우의 레거시 설정 파싱 동작을 검증합니다."""
    conf_file = tmp_path / "rs485.conf"
    conf_file.write_text(LEGACY_SERIAL_CONF)

    with patch("os.getcwd", return_value=str(tmp_path)):
        rs485 = RS485()

        # 1. Wallpad 기기 상태 파싱 검증
        assert rs485._wp_light is True
        assert rs485._wp_fan is False
        assert rs485._wp_thermostat is True
        assert rs485._wp_plug is False
        assert rs485._wp_gas is True
        assert rs485._wp_elevator is False

        # 2. MQTT 설정 파싱 검증
        assert rs485._mqtt["server"] == "192.168.1.50"
        assert rs485._mqtt["anonymous"] == "False"
        assert rs485._mqtt["username"] == "my_user"
        assert rs485._mqtt["password"] == "my_pass"

        # 3. Serial 포트 및 디바이스 파싱 검증
        assert rs485._type == "serial"
        assert rs485._device == {1: "kocom", 2: "grex_ventilator"}
        assert len(rs485._port_url) == 2
        assert rs485._port_url[1] == "/dev/ttyUSB0"
        assert rs485._port_url[2] == "/dev/ttyUSB1"


def test_legacy_rs485_socket(tmp_path, mock_socket):
    """rs485.conf의 type이 socket인 경우의 레거시 설정 파싱 동작을 검증합니다."""
    conf_file = tmp_path / "rs485.conf"
    conf_file.write_text(LEGACY_SOCKET_CONF)

    with patch("os.getcwd", return_value=str(tmp_path)):
        rs485 = RS485()

        # 1. Wallpad 기기 상태 파싱 검증
        assert rs485._wp_light is False
        assert rs485._wp_fan is True
        assert rs485._wp_thermostat is False
        assert rs485._wp_plug is True
        assert rs485._wp_gas is False
        assert rs485._wp_elevator is True

        # 2. MQTT 설정 파싱 검증
        assert rs485._mqtt["server"] == "192.168.1.100"
        assert rs485._mqtt["anonymous"] == "True"

        # 3. Socket 설정 파싱 검증
        assert rs485._type == "socket"
        assert rs485._device == "kocom"

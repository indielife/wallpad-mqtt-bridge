import logging

from wallpad.config import AppConfig
from wallpad.transport.base import BaseTransport
from wallpad.transport.reconnect import ReconnectingTransport
from wallpad.transport.serial import SerialTransport
from wallpad.transport.socket import SocketTransport

logger = logging.getLogger(__name__)


def create_wallpad_transport(config: AppConfig) -> BaseTransport:
    """Wallpad 연결 타입에 맞는 transport를 생성하여 반환합니다."""
    comm_type = config.comm_type
    if comm_type == "serial":
        port = config.serial_port
        if not port:
            raise ValueError("Wallpad serial port is not configured.")
        logger.info("Wallpad Serial Port: %s", port)
        return ReconnectingTransport(SerialTransport(port, 9600))
    elif comm_type == "socket":
        return ReconnectingTransport(SocketTransport(config.socket_host, config.socket_port))
    raise ValueError(f"Invalid Wallpad connection type: {comm_type}")


def create_ventilator_transports(config: AppConfig) -> tuple[BaseTransport, BaseTransport]:
    """Ventilator (ctrl, unit) transport 쌍을 생성하여 반환합니다."""
    ctrl_port = config.ventilator_ctrl_port
    unit_port = config.ventilator_unit_port
    if not ctrl_port or not unit_port:
        raise ValueError("Ventilator serial ports are not fully configured.")
    logger.info("Ventilator ctrl Port: %s", ctrl_port)
    logger.info("Ventilator unit Port: %s", unit_port)
    return (
        ReconnectingTransport(SerialTransport(ctrl_port, 9600)),
        ReconnectingTransport(SerialTransport(unit_port, 9600)),
    )

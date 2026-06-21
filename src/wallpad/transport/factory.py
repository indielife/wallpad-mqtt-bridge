import logging

from wallpad.config import AppConfig
from wallpad.transport.base import BaseTransport
from wallpad.transport.reconnect import ReconnectingTransport
from wallpad.transport.serial import SerialTransport
from wallpad.transport.socket import SocketTransport

logger = logging.getLogger(__name__)


def create_wallpad_transport(config: AppConfig) -> BaseTransport:
    """Wallpad 연결 타입에 맞는 transport를 생성하여 반환합니다."""
    if config.comm_type == "serial":
        logger.info("Wallpad Serial Port: %s", config.serial_port)
        return ReconnectingTransport(SerialTransport(config.serial_port, 9600))
    return ReconnectingTransport(SocketTransport(config.socket_host, config.socket_port))


def create_ventilator_transports(config: AppConfig) -> tuple[BaseTransport, BaseTransport]:
    """Ventilator (ctrl, unit) transport 쌍을 생성하여 반환합니다."""
    logger.info("Ventilator ctrl Port: %s", config.ventilator_ctrl_port)
    logger.info("Ventilator unit Port: %s", config.ventilator_unit_port)
    return (
        ReconnectingTransport(SerialTransport(config.ventilator_ctrl_port, 9600)),
        ReconnectingTransport(SerialTransport(config.ventilator_unit_port, 9600)),
    )

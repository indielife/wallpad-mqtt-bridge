import logging

from wallpad.config import AppConfig
from wallpad.transport.base import ConnectionAdapter
from wallpad.transport.serial import SerialAdapter
from wallpad.transport.socket import SocketAdapter

logger = logging.getLogger(__name__)


def create_wallpad_adapter(config: AppConfig) -> ConnectionAdapter:
    """Wallpad 연결 타입에 맞는 어댑터를 생성하여 반환합니다.

    연결에 실패하면 예외를 발생시킵니다.
    """
    comm_type = config.comm_type
    if comm_type == "serial":
        port = config.serial_port
        if not port:
            raise ValueError("Wallpad serial port is not configured.")
        adapter = SerialAdapter(port, 9600)
        logger.info("Wallpad Serial Port: %s", port)
        return adapter
    elif comm_type == "socket":
        return SocketAdapter(config.socket_host, config.socket_port)
    raise ValueError(f"Invalid Wallpad connection type: {comm_type}")


def create_ventilator_adapters(
    config: AppConfig,
) -> tuple[ConnectionAdapter, ConnectionAdapter]:
    """Ventilator (ctrl, unit) 어댑터 쌍을 생성하여 반환합니다.

    포트가 설정되지 않았거나 연결에 실패하면 예외를 발생시킵니다.
    """
    ctrl_port = config.ventilator_ctrl_port
    unit_port = config.ventilator_unit_port
    if not ctrl_port or not unit_port:
        raise ValueError("Ventilator serial ports are not fully configured.")
    ctrl = SerialAdapter(ctrl_port, 9600)
    logger.info("Ventilator ctrl Port: %s", ctrl_port)
    unit = SerialAdapter(unit_port, 9600)
    logger.info("Ventilator unit Port: %s", unit_port)
    return ctrl, unit

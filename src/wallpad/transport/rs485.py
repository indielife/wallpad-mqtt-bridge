import logging
import socket

import serial

from wallpad.config import AppConfig
from wallpad.transport.serial import SerialAdapter, SerialTransport
from wallpad.transport.socket import SocketAdapter, SocketTransport

logger = logging.getLogger(__name__)


class RS485:
    """Manager class for RS485 connections, instantiating appropriate ConnectionAdapters."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.type = config.comm_type
        self.adapters = {}

    def connect_wallpad(self) -> bool:
        """Wallpad가 enabled일 때, Wallpad 설정에 맞게 포트/소켓을 열어 어댑터를 등록합니다."""
        if not self.config.wallpad_enabled:
            return True

        comm_type = self.config.comm_type
        if comm_type == "serial":
            return self._init_wallpad_serial()
        elif comm_type == "socket":
            return self._init_wallpad_socket()
        else:
            logger.error("Invalid Wallpad connection type: %s", comm_type)
            return False

    def connect_ventilator(self) -> bool:
        """Ventilator가 enabled일 때, 설정에 맞게 포트/소켓을 열어 어댑터를 등록합니다."""
        if not self.config.ventilator_enabled:
            return True

        comm_type = self.config.ventilator_connection_type
        if comm_type == "serial":
            return self._init_ventilator_serial()
        elif comm_type == "socket":
            return self._init_ventilator_socket()
        else:
            logger.error("Invalid Ventilator connection type: %s", comm_type)
            return False

    def _init_wallpad_serial(self) -> bool:
        port_path = self.config.serial_port
        if not port_path:
            logger.error("Wallpad serial port is not configured.")
            return False

        try:
            self.adapters["wallpad"] = SerialAdapter(port_path, 9600)
            logger.info("Wallpad Serial Port: %s", port_path)
            return True
        except Exception as e:
            logger.error("Failed to connect to serial port (%s): %r", port_path, e)
            return False

    def _init_wallpad_socket(self) -> bool:
        server = self.config.socket_server
        port = self.config.socket_port
        try:
            self.adapters["wallpad"] = SocketAdapter(server, port)
            return True
        except Exception as e:
            logger.info("Failed to connect to socket (target: %s:%s, error: %r)", server, port, e)
            return False

    def _init_ventilator_serial(self) -> bool:
        opened = 0
        for role, port_path in [
            ("ventilator_unit", self.config.ventilator_unit_port),
            ("ventilator_ctrl", self.config.ventilator_ctrl_port),
        ]:
            if port_path:
                try:
                    self.adapters[role] = SerialAdapter(port_path, 9600)
                    opened += 1
                except Exception as e:
                    logger.error(
                        "Failed to connect to serial port (Ventilator: %s, port: %s, error: %r)",
                        role,
                        port_path,
                        e,
                    )

        if opened == 0:
            logger.error("No Ventilator serial ports were successfully opened.")
            return False
        return True

    def _init_ventilator_socket(self) -> bool:
        server = self.config.ventilator_socket_server
        port = self.config.ventilator_socket_port

        try:
            self.adapters["ventilator_socket"] = SocketAdapter(server, port)
            return True
        except Exception as e:
            logger.info(
                "Failed to connect to ventilator socket (target: %s:%s, error: %r)",
                server,
                port,
                e,
            )
            return False

import logging
import socket

import serial

from wallpad.config import AppConfig
from wallpad.rs485.serial import SerialAdapter
from wallpad.rs485.socket import SocketAdapter

logger = logging.getLogger(__name__)


class RS485:
    """Manager class for RS485 connections, instantiating appropriate ConnectionAdapters."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._port_url = config.port_url
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
        opened = 0
        for p in self._port_url:
            port_path = self._port_url[p]
            try:
                ser = serial.Serial(port_path, 9600, timeout=None)
                if ser.isOpen():
                    ser.bytesize = 8
                    ser.stopbits = 1
                    ser.autoOpen = False
                    logger.info("Port %s : %s", p, port_path)
                    self.adapters[p] = SerialAdapter(ser)
                    opened += 1
                else:
                    logger.info("Serial port is not open (device: %s, port: %s)", p, port_path)
            except Exception as e:
                logger.info(
                    "Failed to connect to serial port (device: %s, port: %s, error: %r)",
                    p,
                    port_path,
                    e,
                )
        if opened == 0:
            logger.error("No Wallpad serial ports were successfully opened.")
            return False
        return True

    def _init_wallpad_socket(self) -> bool:
        server = self.config.socket_server
        port = self.config.socket_port
        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
            soc.settimeout(None)
            self.adapters[self.config.socket_device] = SocketAdapter(soc)
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
                    ser = serial.Serial(port_path, 9600, timeout=None)
                    if ser.isOpen():
                        ser.bytesize = 8
                        ser.stopbits = 1
                        ser.autoOpen = False
                        logger.info("Ventilator %s Port: %s", role, port_path)
                        self.adapters[role] = SerialAdapter(ser)
                        opened += 1
                    else:
                        logger.info(
                            "Serial port is not open (Ventilator: %s, port: %s)",
                            role,
                            port_path,
                        )
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
        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
            soc.settimeout(None)
            self.adapters["ventilator_socket"] = SocketAdapter(soc)
            return True
        except Exception as e:
            logger.info(
                "Failed to connect to ventilator socket (target: %s:%s, error: %r)",
                server,
                port,
                e,
            )
            return False

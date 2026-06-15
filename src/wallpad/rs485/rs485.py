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
        self._device_list = config.device_list
        self._socket_device = config.socket_device
        self.type = config.comm_type
        self.adapters = {}

        if self.type == "serial":
            self._init_serial()
        elif self.type == "socket":
            self._init_socket()
        else:
            logger.error("Invalid communication type: %s (must be serial or socket)", self.type)
            logger.error("Exiting RS485 initialization")
            exit(1)

    @property
    def _device(self):
        if self.type == "serial":
            return self._device_list
        elif self.type == "socket":
            return self._socket_device

    @property
    def _type(self):
        return self.type

    @property
    def _connect(self):
        return self.adapters

    def _init_serial(self):
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
            logger.error("No serial ports were successfully opened.")

    def _init_socket(self):
        server = self.config.socket_server
        port = self.config.socket_port
        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
            soc.settimeout(None)
            self.adapters[self._socket_device] = SocketAdapter(soc)
        except Exception as e:
            logger.info("Failed to connect to socket (target: %s:%s, error: %r)", server, port, e)

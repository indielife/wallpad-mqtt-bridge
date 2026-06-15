import logging
import socket

import serial

from wallpad.config import AppConfig

logger = logging.getLogger(__name__)


class RS485:
    def __init__(self, config: AppConfig):
        self.config = config
        self._mqtt_config = config.mqtt_config
        self._port_url = config.port_url
        self._device_list = config.device_list
        self._wp_list = config.wp_list
        self.type = None

        d_type = config.comm_type
        if d_type == "serial":
            self.type = d_type
            self._con = self.connect_serial(self._port_url)
        elif d_type == "socket":
            self.type = d_type
            self._socket_device = config.socket_device
            self._con = self.connect_socket(config.socket_server, config.socket_port)
        else:
            logger.error("Invalid communication type: %s (must be serial or socket)", d_type)
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
        return self._con

    def connect_serial(self, port):
        ser = {}
        opened = 0
        for p in port:
            try:
                ser[p] = serial.Serial(port[p], 9600, timeout=None)
                if ser[p].isOpen():
                    ser[p].bytesize = 8
                    ser[p].stopbits = 1
                    ser[p].autoOpen = False
                    logger.info("Port %s : %s", p, port[p])
                    opened += 1
                else:
                    logger.info("Serial port is not open (device: %s, port: %s)", p, port[p])
            except Exception as e:
                logger.info(
                    "Failed to connect to serial port (device: %s, port: %s, error: %r)",
                    p,
                    port[p],
                    e,
                )
        if opened == 0:
            return False
        return ser

    def connect_socket(self, server, port):
        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
        except Exception as e:
            logger.info("Failed to connect to socket (target: %s:%s, error: %r)", server, port, e)
            return False
        soc.settimeout(None)
        return soc

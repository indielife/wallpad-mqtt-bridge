import logging
import socket

import serial

from kocom.config import AppConfig

logger = logging.getLogger(__name__)

CONF_MQTT = "MQTT"


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
            logger.info("[CONFIG] SERIAL / SOCKET IS NOT VALID")
            logger.info("[CONFIG] EXIT RS485")
            exit(1)

    @property
    def _wp_light(self):
        return self.config.wp_light

    @property
    def _wp_fan(self):
        return self.config.wp_fan

    @property
    def _wp_thermostat(self):
        return self.config.wp_thermostat

    @property
    def _wp_plug(self):
        return self.config.wp_plug

    @property
    def _wp_gas(self):
        return self.config.wp_gas

    @property
    def _wp_elevator(self):
        return self.config.wp_elevator

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

    @property
    def _mqtt(self):
        return self._mqtt_config

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
                    logger.info("시리얼포트가 열려있지 않습니다.[%s]", port[p])
            except serial.serialutil.SerialException:
                logger.info("시리얼포트에 연결할 수 없습니다.[%s]", port[p])
        if opened == 0:
            return False
        return ser

    def connect_socket(self, server, port):
        soc = socket.socket()
        soc.settimeout(10)
        try:
            soc.connect((server, int(port)))
        except Exception as e:
            logger.info("소켓에 연결할 수 없습니다.[%s][%s:%s]", e, server, port)
            return False
        soc.settimeout(None)
        return soc

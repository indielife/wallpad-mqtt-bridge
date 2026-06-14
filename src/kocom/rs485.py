import configparser
import logging
import os
import socket

import serial

logger = logging.getLogger(__name__)

# CONFIG 파일 변수값
CONF_FILE = "rs485.conf"
CONF_LOGNAME = "RS485"
CONF_WALLPAD = "Wallpad"
CONF_MQTT = "MQTT"
CONF_DEVICE = "RS485"
CONF_SERIAL = "Serial"
CONF_SERIAL_DEVICE = "SerialDevice"
CONF_SOCKET = "Socket"
CONF_SOCKET_DEVICE = "SocketDevice"


class RS485:
    def __init__(self):
        self._mqtt_config = {}
        self._port_url = {}
        self._device_list = {}
        self._wp_list = {}
        self.type = None

        root_dir = os.path.abspath(os.getcwd())
        conf_path = str(root_dir + "/" + CONF_FILE)

        config = configparser.ConfigParser()
        config.read(conf_path)

        get_conf_wallpad = config.items(CONF_WALLPAD)
        for item in get_conf_wallpad:
            self._wp_list.setdefault(item[0], item[1])
            logger.info("[CONFIG] %s %s : %s", CONF_WALLPAD, item[0], item[1])

        get_conf_mqtt = config.items(CONF_MQTT)
        for item in get_conf_mqtt:
            self._mqtt_config.setdefault(item[0], item[1])
            logger.info("[CONFIG] %s %s : %s", CONF_MQTT, item[0], item[1])

        d_type = config.get(CONF_LOGNAME, "type").lower()
        if d_type == "serial":
            self.type = d_type
            get_conf_serial = config.items(CONF_SERIAL)
            port_i = 1
            for item in get_conf_serial:
                if item[1] != "":
                    self._port_url.setdefault(port_i, item[1])
                    logger.info("[CONFIG] %s %s : %s", CONF_SERIAL, item[0], item[1])
                port_i += 1

            get_conf_serial_device = config.items(CONF_SERIAL_DEVICE)
            port_i = 1
            for item in get_conf_serial_device:
                if item[1] != "":
                    self._device_list.setdefault(port_i, item[1])
                    logger.info("[CONFIG] %s %s : %s", CONF_SERIAL_DEVICE, item[0], item[1])
                port_i += 1
            self._con = self.connect_serial(self._port_url)
        elif d_type == "socket":
            self.type = d_type
            server = config.get(CONF_SOCKET, "server")
            port = config.get(CONF_SOCKET, "port")
            self._socket_device = config.get(CONF_SOCKET_DEVICE, "device")
            self._con = self.connect_socket(server, port)
        else:
            logger.info("[CONFIG] SERIAL / SOCKET IS NOT VALID")
            logger.info("[CONFIG] EXIT RS485")
            exit(1)

    @property
    def _wp_light(self):
        return self._wp_list.get("light") == "True"

    @property
    def _wp_fan(self):
        return self._wp_list.get("fan") == "True"

    @property
    def _wp_thermostat(self):
        return self._wp_list.get("thermostat") == "True"

    @property
    def _wp_plug(self):
        return self._wp_list.get("plug") == "True"

    @property
    def _wp_gas(self):
        return self._wp_list.get("gas") == "True"

    @property
    def _wp_elevator(self):
        return self._wp_list.get("elevator") == "True"

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

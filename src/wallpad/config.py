import configparser
import json
import logging
import os

from wallpad.mqtt import MqttConfig
from wallpad.version import SW_VERSION

logger = logging.getLogger(__name__)


KOCOM_LIGHT_SIZE_DEFAULT = {
    "livingroom": 3,
    "bedroom": 2,
    "room1": 2,
    "room2": 2,
    "kitchen": 3,
}

KOCOM_PLUG_SIZE_DEFAULT = {
    "livingroom": 2,
    "bedroom": 2,
    "room1": 2,
    "room2": 2,
    "kitchen": 2,
}

KOCOM_ROOM_DEFAULT = {
    "00": "livingroom",
    "01": "bedroom",
    "02": "room2",
    "03": "room1",
    "04": "kitchen",
}

KOCOM_ROOM_THERMOSTAT_DEFAULT = {
    "00": "livingroom",
    "01": "bedroom",
    "02": "room1",
    "03": "room2",
}


class AppConfig:
    """
    HA의 options.json 파일에서 설정을 읽어와 저장하는 순수 데이터 클래스입니다.
    통신 포트(Serial/Socket) 연결 등 사이드 이펙트를 발생시키지 않습니다.
    """

    def __init__(self, options_path="/data/options.json"):
        self.options_path = options_path

        self.sw_version = SW_VERSION

        # 1. MQTT Broker 설정
        self.mqtt_config: MqttConfig = None

        # 2. Wallpad 설정
        self.wallpad_manufacturer = "kocom"

        # 3. RS485 & 하드웨어 통신 설정
        self.comm_type = None
        self.port_url = {}
        self.device_list = {}
        self.socket_server = None
        self.socket_port = None
        self.socket_device = None

        # 4. 기기 활성화 정보 (Enabled Devices)
        self.wp_list = {}

        # 5. Advanced 세부 제어 설정
        self.init_temp = 22
        self.scan_interval = 300
        self.packey_delay = 0.8
        self.kocom_default_speed = "low"
        self.log_level = "info"

        # 6. Kocom 사이즈 및 방 이름 매핑 설정
        self.kocom_light_size = dict(KOCOM_LIGHT_SIZE_DEFAULT)
        self.kocom_plug_size = dict(KOCOM_PLUG_SIZE_DEFAULT)
        self.kocom_room = dict(KOCOM_ROOM_DEFAULT)
        self.kocom_room_thermostat = dict(KOCOM_ROOM_THERMOSTAT_DEFAULT)

        # 7. Ventilator(전열교환기) 설정
        self.ventilator_manufacturer = "none"
        self.ventilator_connection_type = "serial"
        self.ventilator_socket_server = ""
        self.ventilator_socket_port = 8899
        self.ventilator_ctrl_port = ""
        self.ventilator_unit_port = ""
        self.ventilator_default_speed = "low"

    def load(self):
        """설정 파일을 로드합니다."""
        self._load_options_json()

    def _parse_serial_ports(self, serial_data: dict) -> dict:
        ports = {}
        for k, v in serial_data.items():
            if not v:
                continue
            k_lower = k.lower()
            if k_lower == "port":
                ports[1] = v
            elif k_lower.startswith("port"):
                try:
                    port_num = int(k_lower[4:])
                    ports[port_num] = v
                except ValueError:
                    pass
        return ports

    def _load_options_json(self):
        if not os.path.isfile(self.options_path):
            logger.debug(
                "options.json 파일을 찾을 수 없습니다. 기본값을 사용합니다: %s", self.options_path
            )
            return

        with open(self.options_path, encoding="utf-8") as json_file:
            json_data = json.load(json_file)

        # 1. MQTT Broker 설정
        mqtt_json = json_data.get("MQTT Broker", {})
        self.mqtt_config = MqttConfig(
            server=mqtt_json.get("Server", ""),
            username=mqtt_json.get("Username", ""),
            password=mqtt_json.get("Password", ""),
        )

        # 2. Wallpad 설정
        wallpad_json = json_data.get("Wallpad", {})
        wp_mfg = wallpad_json.get("Manufacturer", "kocom")
        self.wallpad_manufacturer = wp_mfg.lower() if isinstance(wp_mfg, str) else "kocom"

        # 3. RS485 & 하드웨어 통신 설정
        rs485_type = json_data.get("RS485", {}).get("type", "Serial")
        self.comm_type = wallpad_json.get("Connection Type", rs485_type).lower()

        serial_data = wallpad_json.get("Serial", json_data.get("Serial", {}))
        self.port_url = self._parse_serial_ports(serial_data)
        self.device_list = {port_num: self.wallpad_manufacturer for port_num in self.port_url}

        soc = wallpad_json.get("Socket", json_data.get("Socket", {}))
        self.socket_server = soc.get("Server")
        self.socket_port = soc.get("Port")
        self.socket_device = self.wallpad_manufacturer

        # 4. 기기 활성화 설정 (Enabled Devices)
        self.wp_list = wallpad_json.get("Enabled Devices", {})

        # 5. Advanced 세부 제어 설정
        adv = json_data.get("Advanced", {})
        self.init_temp = adv.get("INIT_TEMP", self.init_temp)
        self.scan_interval = adv.get("SCAN_INTERVAL", self.scan_interval)
        self.packey_delay = adv.get("PACKET_DELAY", self.packey_delay)
        self.kocom_default_speed = adv.get("DEFAULT_SPEED", self.kocom_default_speed)
        self.log_level = adv.get("LOGLEVEL", self.log_level).lower()

        # 6. Kocom 사이즈 및 방 이름 매핑 설정
        kocom_light_size_list = json_data.get("KOCOM_LIGHT_SIZE", [])
        if kocom_light_size_list:
            self.kocom_light_size = {}
            for i in kocom_light_size_list:
                self.kocom_light_size[i["name"]] = i["number"]

        kocom_plug_size_list = json_data.get("KOCOM_PLUG_SIZE", [])
        if kocom_plug_size_list:
            self.kocom_plug_size = {}
            for i in kocom_plug_size_list:
                self.kocom_plug_size[i["name"]] = i["number"]

        kocom_room_list = json_data.get("KOCOM_ROOM", [])
        if kocom_room_list:
            self.kocom_room = {}
            for num, i in enumerate(kocom_room_list):
                self.kocom_room[f"{num:02d}"] = i

        kocom_room_thermostat_list = json_data.get("KOCOM_ROOM_THERMOSTAT", [])
        if kocom_room_thermostat_list:
            self.kocom_room_thermostat = {}
            for num, i in enumerate(kocom_room_thermostat_list):
                self.kocom_room_thermostat[f"{num:02d}"] = i

        # 7. Ventilator(전열교환기) 설정
        vent = json_data.get("Ventilator", {})
        vent_mfg = vent.get("Manufacturer", vent.get("manufacturer", "none"))
        self.ventilator_manufacturer = vent_mfg.lower() if isinstance(vent_mfg, str) else "none"
        self.ventilator_connection_type = vent.get(
            "Connection Type", vent.get("connection_type", "Serial")
        ).lower()

        vent_socket = vent.get("Socket", {})
        self.ventilator_socket_server = vent_socket.get("Server", vent_socket.get("server", ""))
        self.ventilator_socket_port = vent_socket.get("Port", vent_socket.get("port", 8899))

        vent_serial = vent.get("Serial", {})
        self.ventilator_ctrl_port = vent_serial.get(
            "Controller Port", vent_serial.get("controller_port", "")
        )
        self.ventilator_unit_port = vent_serial.get(
            "Ventilator Port", vent_serial.get("ventilator_port", "")
        )

        self.ventilator_default_speed = vent.get(
            "Default Speed", vent.get("default_speed", self.ventilator_default_speed)
        )

    @property
    def ventilator(self) -> str:
        return self.ventilator_manufacturer

    @property
    def wallpad(self) -> str:
        return self.wallpad_manufacturer

    @property
    def wp_light(self) -> bool:
        return self.wp_list.get("light") is True

    @property
    def wp_fan(self) -> bool:
        return self.wp_list.get("fan") is True

    @property
    def wp_thermostat(self) -> bool:
        return self.wp_list.get("thermostat") is True

    @property
    def wp_plug(self) -> bool:
        return self.wp_list.get("plug") is True

    @property
    def wp_gas(self) -> bool:
        return self.wp_list.get("gas") is True

    @property
    def wp_elevator(self) -> bool:
        return self.wp_list.get("elevator") is True

    @property
    def kocom_room_rev(self):
        """방 이름에서 패킷 식별용 16진수 문자열로의 역방향 매핑입니다."""
        rev = {v: k for k, v in self.kocom_room.items()}
        rev["wallpad"] = "00"
        return rev

    @property
    def kocom_room_thermostat_rev(self):
        """난방기 방 이름에서 패킷 식별용 16진수 문자열로의 역방향 매핑입니다."""
        return {v: k for k, v in self.kocom_room_thermostat.items()}

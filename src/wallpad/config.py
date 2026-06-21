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
        self._wallpad_enabled = True
        self.wallpad_manufacturer = "kocom"

        # 3. RS485 & 하드웨어 통신 설정
        self.comm_type = None
        self.serial_port = ""
        self.socket_host = None
        self.socket_port = None

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
        self._ventilator_enabled = False
        self.ventilator_manufacturer = "none"
        self.ventilator_connection_type = "serial"
        self.ventilator_socket_host = ""
        self.ventilator_socket_port = 8899
        self.ventilator_ctrl_port = ""
        self.ventilator_unit_port = ""
        self.ventilator_default_speed = "low"

    def load(self):
        """설정 파일을 로드합니다."""
        self._load_options_json()

    def _load_options_json(self):
        if not os.path.isfile(self.options_path):
            logger.debug(
                "options.json 파일을 찾을 수 없습니다. 기본값을 사용합니다: %s", self.options_path
            )
            return

        with open(self.options_path, encoding="utf-8") as json_file:
            json_data = json.load(json_file)

        # 1. MQTT Broker 설정
        mqtt_json = json_data.get("mqtt_broker", {})
        self.mqtt_config = MqttConfig(
            host=os.environ.get("MQTT_HOST") or mqtt_json.get("host", ""),
            username=os.environ.get("MQTT_USERNAME") or mqtt_json.get("username", ""),
            password=os.environ.get("MQTT_PASSWORD") or mqtt_json.get("password", ""),
        )

        # 2. Wallpad 설정
        wallpad_json = json_data.get("wallpad", {})
        self._wallpad_enabled = wallpad_json.get("enable", True)
        wp_mfg = wallpad_json.get("manufacturer", "kocom")
        self.wallpad_manufacturer = wp_mfg.lower() if isinstance(wp_mfg, str) else "kocom"

        # 3. RS485 & 하드웨어 통신 설정
        self.comm_type = wallpad_json.get("connection_type", "Serial").lower()

        serial_data = wallpad_json.get("serial", {})
        self.serial_port = serial_data.get("port", "")

        soc = wallpad_json.get("socket", {})
        self.socket_host = os.environ.get("WALLPAD_HOST") or soc.get("host")
        self.socket_port = soc.get("port")

        # 4. 기기 활성화 설정 (enabled_devices)
        self.wp_list = wallpad_json.get("enabled_devices", {})

        # 5. Advanced 세부 제어 설정
        adv = json_data.get("advanced", {})
        self.init_temp = adv.get("init_temp", self.init_temp)
        self.scan_interval = adv.get("scan_interval", self.scan_interval)
        self.packey_delay = adv.get("packet_delay", self.packey_delay)
        self.kocom_default_speed = adv.get("default_speed", self.kocom_default_speed)
        self.log_level = adv.get("loglevel", self.log_level).lower()

        # 6. Kocom 사이즈 및 방 이름 매핑 설정
        kocom_light_size_list = json_data.get("kocom_light_size", [])
        if kocom_light_size_list:
            self.kocom_light_size = {}
            for i in kocom_light_size_list:
                self.kocom_light_size[i["name"]] = i["number"]

        kocom_plug_size_list = json_data.get("kocom_plug_size", [])
        if kocom_plug_size_list:
            self.kocom_plug_size = {}
            for i in kocom_plug_size_list:
                self.kocom_plug_size[i["name"]] = i["number"]

        kocom_room_list = json_data.get("kocom_room", [])
        if kocom_room_list:
            self.kocom_room = {}
            for num, i in enumerate(kocom_room_list):
                self.kocom_room[f"{num:02d}"] = i

        kocom_room_thermostat_list = json_data.get("kocom_room_thermostat", [])
        if kocom_room_thermostat_list:
            self.kocom_room_thermostat = {}
            for num, i in enumerate(kocom_room_thermostat_list):
                self.kocom_room_thermostat[f"{num:02d}"] = i

        # 7. Ventilator(전열교환기) 설정
        vent = json_data.get("ventilator", {})
        self._ventilator_enabled = vent.get("enable", False)
        vent_mfg = vent.get("manufacturer", "none")
        self.ventilator_manufacturer = vent_mfg.lower() if isinstance(vent_mfg, str) else "none"
        self.ventilator_connection_type = vent.get("connection_type", "Serial").lower()

        vent_socket = vent.get("socket", {})
        self.ventilator_socket_host = vent_socket.get("host", "")
        self.ventilator_socket_port = vent_socket.get("port", 8899)

        vent_serial = vent.get("serial", {})
        self.ventilator_ctrl_port = vent_serial.get("controller_port", "")
        self.ventilator_unit_port = vent_serial.get("ventilator_port", "")

        self.ventilator_default_speed = vent.get("default_speed", self.ventilator_default_speed)

    def validate(self) -> None:
        """AppConfig 필수값 검증. 유효하지 않으면 ValueError를 발생시킵니다."""
        self._validate_wallpad()
        if self._ventilator_enabled:
            self._validate_ventilator()

    def _validate_wallpad(self) -> None:
        if self.comm_type == "serial":
            if not self.serial_port:
                raise ValueError("Wallpad serial port is not configured.")
        elif self.comm_type == "socket":
            if not self.socket_host:
                raise ValueError("Wallpad socket host is not configured.")

    def _validate_ventilator(self) -> None:
        if self.ventilator_connection_type == "serial":
            if not self.ventilator_ctrl_port or not self.ventilator_unit_port:
                raise ValueError("Ventilator serial ports are not fully configured.")
        elif self.ventilator_connection_type == "socket":
            if not self.ventilator_socket_host:
                raise ValueError("Ventilator socket host is not configured.")

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

    @property
    def wallpad_enabled(self) -> bool:
        return self._wallpad_enabled

    @property
    def ventilator_enabled(self) -> bool:
        return self._ventilator_enabled

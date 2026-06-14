import configparser
import json
import logging
import os

from kocom.constants import SW_VERSION

logger = logging.getLogger(__name__)


class AppConfig:
    """
    HA의 options.json 파일에서 설정을 읽어와 저장하는 순수 데이터 클래스입니다.
    통신 포트(Serial/Socket) 연결 등 사이드 이펙트를 발생시키지 않습니다.
    """

    def __init__(self, options_path="/data/options.json"):
        self.options_path = options_path

        self.sw_version = SW_VERSION
        # options.json 설정 변수
        self.init_temp = 22
        self.scan_interval = 300
        self.packey_delay = 0.8
        self.default_speed = "medium"
        self.log_level = "info"

        self.kocom_light_size = {}
        self.kocom_plug_size = {}
        self.kocom_room = {}
        self.kocom_room_thermostat = {}

        # 통신 및 장치 설정 변수 (기존 rs485.conf 대체)
        self.wp_list = {}
        self.mqtt_config = {}
        self.comm_type = None
        self.port_url = {}
        self.device_list = {}
        self.socket_server = None
        self.socket_port = None
        self.socket_device = None

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

        adv = json_data.get("Advanced", {})
        self.init_temp = adv.get("INIT_TEMP", self.init_temp)
        self.scan_interval = adv.get("SCAN_INTERVAL", self.scan_interval)
        self.packey_delay = adv.get("PACKET_DELAY", self.packey_delay)
        self.default_speed = adv.get("DEFAULT_SPEED", self.default_speed)
        self.log_level = adv.get("LOGLEVEL", self.log_level).lower()

        for i in json_data.get("KOCOM_LIGHT_SIZE", []):
            self.kocom_light_size[i["name"]] = i["number"]

        for i in json_data.get("KOCOM_PLUG_SIZE", []):
            self.kocom_plug_size[i["name"]] = i["number"]

        for num, i in enumerate(json_data.get("KOCOM_ROOM", [])):
            self.kocom_room[f"{num:02d}"] = i

        for num, i in enumerate(json_data.get("KOCOM_ROOM_THERMOSTAT", [])):
            self.kocom_room_thermostat[f"{num:02d}"] = i

        # 통신 및 장치 설정 (기존 rs485.conf의 역할)
        self.comm_type = json_data.get("RS485", {}).get("type", "Serial").lower()

        self.port_url = {int(k[-1]): v for k, v in json_data.get("Serial", {}).items() if v}
        self.device_list = {
            int(k[-1]): v for k, v in json_data.get("SerialDevice", {}).items() if v
        }

        soc = json_data.get("Socket", {})
        self.socket_server = soc.get("server")
        self.socket_port = soc.get("port")
        self.socket_device = json_data.get("SocketDevice", {}).get("device")

        self.mqtt_config = json_data.get("MQTT", {})
        self.wp_list = json_data.get("Wallpad", {})

import json
import logging
import os
from dataclasses import dataclass

from wallpad.mqtt import MqttConfig
from wallpad.version import SW_VERSION

logger = logging.getLogger(__name__)


@dataclass
class RoomConfig:
    """방 하나의 모든 기기 정보를 담는 설정 단위입니다."""

    name: str
    room_no: int | None = None  # 조명/콘센트 패킷 인덱스 (없으면 조명/콘센트 없음)
    light_count: int = 0
    plug_count: int = 0
    thermo_no: int | None = None  # 난방 패킷 인덱스 (없으면 난방 없음)

    @property
    def light_addr(self) -> str | None:
        """조명/콘센트 패킷 주소 (16진수 2자리 문자열)"""
        return f"{self.room_no:02d}" if self.room_no is not None else None

    @property
    def thermo_addr(self) -> str | None:
        """난방 패킷 주소 (16진수 2자리 문자열)"""
        return f"{self.thermo_no:02d}" if self.thermo_no is not None else None


# room2/room1의 조명(02/03)과 난방(03/02) 주소가 교차하는 것이 코콤 기본 배선입니다.
ROOMS_DEFAULT: list[RoomConfig] = [
    RoomConfig("livingroom", room_no=0, light_count=3, plug_count=2, thermo_no=0),
    RoomConfig("bedroom", room_no=1, light_count=2, plug_count=2, thermo_no=1),
    RoomConfig("room2", room_no=2, light_count=2, plug_count=2, thermo_no=3),
    RoomConfig("room1", room_no=3, light_count=2, plug_count=2, thermo_no=2),
    RoomConfig("kitchen", room_no=4, light_count=3, plug_count=2),
]


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

        # 4. 집 전체 단위 기기 활성화 (방 개념 없음)
        self.wp_list = {}

        # 5. Advanced 세부 제어 설정
        self.init_temp = 22
        self.scan_interval = 300
        self.packey_delay = 0.8
        self.kocom_default_speed = "low"
        self.log_level = "info"

        # 6. 방 기반 기기 설정 (조명/콘센트/난방)
        self.rooms: list[RoomConfig] = list(ROOMS_DEFAULT)

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

        # 4. 집 전체 단위 기기 활성화 (fan/gas/elevator)
        self.wp_list = wallpad_json.get("enabled_devices", {})

        # 5. Advanced 세부 제어 설정
        adv = json_data.get("advanced", {})
        self.init_temp = adv.get("init_temp", self.init_temp)
        self.scan_interval = adv.get("scan_interval", self.scan_interval)
        self.packey_delay = adv.get("packet_delay", self.packey_delay)
        self.kocom_default_speed = adv.get("default_speed", self.kocom_default_speed)
        self.log_level = adv.get("loglevel", self.log_level).lower()

        # 6. 방 기반 기기 설정 (wallpad 섹션 하위)
        rooms_list = wallpad_json.get("rooms", [])
        if rooms_list:
            self.rooms = [
                RoomConfig(
                    name=r["name"],
                    room_no=r.get("room_no"),
                    light_count=r.get("light_count", 0),
                    plug_count=r.get("plug_count", 0),
                    thermo_no=r.get("thermo_no"),
                )
                for r in rooms_list
            ]

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
        elif self.comm_type == "socket" and not self.socket_host:
            raise ValueError("Wallpad socket host is not configured.")

    def _validate_ventilator(self) -> None:
        if self.ventilator_connection_type == "socket":
            raise ValueError("Ventilator socket connection is not yet supported.")
        if not self.ventilator_ctrl_port or not self.ventilator_unit_port:
            raise ValueError("Ventilator serial ports are not fully configured.")

    # --- 패킷 디코딩용 순방향 매핑 (주소 → 방 이름) ---

    @property
    def kocom_room(self) -> dict[str, str]:
        """조명/콘센트 패킷 주소 → 방 이름"""
        return {r.light_addr: r.name for r in self.rooms if r.light_addr is not None}

    @property
    def kocom_room_thermostat(self) -> dict[str, str]:
        """난방 패킷 주소 → 방 이름"""
        return {r.thermo_addr: r.name for r in self.rooms if r.thermo_addr is not None}

    # --- 패킷 빌딩용 역방향 매핑 (방 이름 → 주소) ---

    @property
    def kocom_room_rev(self) -> dict[str, str]:
        rev = {r.name: r.light_addr for r in self.rooms if r.light_addr is not None}
        rev["wallpad"] = "00"
        return rev

    @property
    def kocom_room_thermostat_rev(self) -> dict[str, str]:
        return {r.name: r.thermo_addr for r in self.rooms if r.thermo_addr is not None}

    # --- parse_switch에서 방별 기기 개수 조회용 ---

    @property
    def kocom_light_size(self) -> dict[str, int]:
        return {r.name: r.light_count for r in self.rooms if r.light_addr is not None}

    @property
    def kocom_plug_size(self) -> dict[str, int]:
        return {r.name: r.plug_count for r in self.rooms if r.light_addr is not None}

    # --- 집 전체 단위 기기 활성화 여부 ---

    @property
    def wp_fan(self) -> bool:
        return self.wp_list.get("fan") is True

    @property
    def wp_gas(self) -> bool:
        return self.wp_list.get("gas") is True

    @property
    def wp_elevator(self) -> bool:
        return self.wp_list.get("elevator") is True

    @property
    def ventilator(self) -> str:
        return self.ventilator_manufacturer

    @property
    def wallpad(self) -> str:
        return self.wallpad_manufacturer

    @property
    def wallpad_enabled(self) -> bool:
        return self._wallpad_enabled

    @property
    def ventilator_enabled(self) -> bool:
        return self._ventilator_enabled

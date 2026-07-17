from wallpad.devices.packet_builder import PacketBuilder
from wallpad.devices.topic import TopicContext
from wallpad.protocol.base import HardwareInfo


class BaseDevice:
    """
    모든 월패드/환기장치 디바이스의 기본이 되는 추상화 클래스입니다.
    """

    def __init__(
        self,
        name_prefix: str,
        room: str,
        sub_device: str,
        sw_version: str,
        hw_info: HardwareInfo,
        packet_builder: PacketBuilder | None = None,
        topics: TopicContext | None = None,
    ):
        self.name_prefix = name_prefix
        self.room = room
        self.sub_device = sub_device
        self.sw_version = sw_version
        self.hw_info = hw_info
        self.packet_builder = packet_builder
        self.topics = topics

    @property
    def device_info(self) -> dict:
        """HA Discovery에 등록될 물리적 기기(Device)의 공통 메타데이터입니다."""
        hw = self.hw_info
        return {
            "identifiers": f"{hw.slug}_{self.room}",
            "name": f"{hw.slug} {self.room}",
            "manufacturer": hw.manufacturer,
            "model": hw.model,
            "sw_version": self.sw_version,
        }

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        """
        MQTT Discovery에 등록할 (topic, payload_json) 튜플의 리스트를 반환합니다.
        remove=True 인 경우 기기 삭제를 위해 payload_json은 빈 문자열("")이 되어야 합니다.
        """
        raise NotImplementedError

    def get_subscribe_topics(self) -> list[str]:
        """
        해당 기기를 제어하기 위해 subscribe 해야 하는 토픽 문자열 리스트를 반환합니다.
        """
        if self.topics:
            return self.topics.config_topics + self.topics.command_topics
        raise NotImplementedError

    def get_command_topics(self) -> list[str]:
        """
        HA에서 수신할 command topic 문자열 리스트를 반환합니다. config topic은 제외합니다.
        """
        if self.topics:
            return self.topics.command_topics
        raise NotImplementedError

    def resolve_command(self, command: str, payload: str) -> tuple[str, str, str, str] | None:
        """
        HA 명령을 (device_type, room, sub_device, processed_payload)로 변환합니다.
        None 반환 시 parse_message가 처리를 스킵합니다.
        """
        raise NotImplementedError

    def get_optimistic_state(self, device_states) -> object | None:
        """
        HA 명령 반영(apply_ha_command) 직후 즉시 publish할 HA 상태를 반환합니다.
        None 반환 시 publish 스킵 (RS485 ack 후 publish).
        """
        return None

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        """
        HA에 발행할 (topic, payload) 튜플 리스트를 반환합니다.
        대부분의 기기는 1개, Gas처럼 복수 토픽이 필요한 경우 여러 개를 반환합니다.
        """
        raise NotImplementedError

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        """
        명령 패킷(16진수 문자열) 전체를 생성하여 반환합니다.
        오버라이딩하지 않은 경우 None을 반환하여 main.py의 레거시 로직을 따릅니다.
        """
        return None

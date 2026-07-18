import json
from typing import ClassVar

from wallpad.apps.ventilator.devices.base import VentilatorDevice
from wallpad.mqtt import HA_FAN, HA_PREFIX
from wallpad.protocol.grex.constants import MODE_HEX_MAP, SPEED_HEX_MAP


class VentilatorUnit(VentilatorDevice):
    """HA fan 도메인을 담당하는 환기장치 본체입니다."""

    MODE_HEX_MAP: ClassVar[dict[str, str]] = MODE_HEX_MAP
    SPEED_HEX_MAP: ClassVar[dict[str, str]] = SPEED_HEX_MAP

    @property
    def state_topic(self) -> str:
        """HA fan 엔티티의 상태 토픽입니다."""
        return f"{HA_PREFIX}/{HA_FAN}/{self.room}/state"

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        config_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        if remove:
            return [(config_topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.sub_device}",
            "command_topic": f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode",
            "state_topic": self.state_topic,
            "spd_cmd_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed",
            "spd_stat_t": self.state_topic,
            "state_value_template": "{{ value_json.mode }}",
            "spd_val_tpl": "{{ value_json.speed }}",
            "payload_on": "on",
            "payload_off": "off",
            "spds": ["low", "medium", "high", "off"],
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(config_topic, json.dumps(payload))]

    def get_subscribe_topics(self) -> list[str]:
        config_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode"
        spd_cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed"
        return [config_topic, command_topic, spd_cmd_t]

    def resolve_command_key(self, topic: str) -> str | None:
        """구독 토픽을 fan 명령 키(mode/speed)로 변환합니다.

        discovery config 토픽 echo나 명령이 아닌 토픽은 None을 반환합니다.
        """
        if topic.endswith("/config"):
            return None
        key = topic.rsplit("/", 1)[-1]
        return key if key in ("mode", "speed") else None

    def build_control_packet(self, mode: str, speed: str) -> str:
        """환기장치 본체를 제어하기 위한 패킷을 생성합니다."""
        if not self.packet_builder:
            return ""

        mode_hex = self.MODE_HEX_MAP.get(mode)
        speed_hex = self.SPEED_HEX_MAP.get(speed)

        if not mode_hex or not speed_hex:
            return ""

        if ((mode == "auto" or mode == "sleep") and (speed == "off")) or (
            speed in ["low", "medium", "high"]
        ):
            postfix_hex = "0001"
        else:
            postfix_hex = "0000"

        return self.packet_builder.build_control(mode_hex, speed_hex, postfix_hex)

    def build_response_packet(self, mode: str, speed: str) -> str:
        """월패드 컨트롤러에 상태를 동기화하기 위한 응답 패킷을 생성합니다."""
        if not self.packet_builder:
            return ""

        speed_hex = self.SPEED_HEX_MAP.get(speed, "0000")
        postfix_hex = "0000000100" if speed in ["low", "medium", "high"] else "0000000000"

        return self.packet_builder.build_response(speed_hex, postfix_hex)

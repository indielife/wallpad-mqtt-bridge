import json
from typing import ClassVar

from wallpad.devices.base import BaseDevice
from wallpad.mqtt import HA_FAN, HA_PREFIX, HA_SENSOR
from wallpad.protocol.grex.constants import MODE_HEX_MAP, SPEED_HEX_MAP
from wallpad.protocol.grex.packet_builder import GrexPacketBuilder


class GrexVentilator(BaseDevice):
    MODE_HEX_MAP: ClassVar[dict[str, str]] = MODE_HEX_MAP
    SPEED_HEX_MAP: ClassVar[dict[str, str]] = SPEED_HEX_MAP

    def __init__(
        self, name_prefix: str, sw_version: str, packet_builder: GrexPacketBuilder | None = None
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="grex",
            sub_device="fan",
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    @property
    def device_info(self) -> dict:
        """Grex 고유의 기기 메타데이터를 반환하도록 오버라이딩합니다."""
        return {
            "name": "Grex Ventilator",
            "identifiers": "grex_ventilator",
            "manufacturer": "Grex",
            "model": "Ventilator",
            "sw_version": self.sw_version,
        }

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        fan_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        mode_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_mode/config"
        speed_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_speed/config"

        if remove:
            return [(fan_topic, ""), (mode_topic, ""), (speed_topic, "")]

        fan_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}",
            "command_topic": f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode",
            "state_topic": f"{HA_PREFIX}/{HA_FAN}/{self.room}/state",
            "spd_cmd_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed",
            "spd_stat_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/state",
            "state_value_template": "{{ value_json.mode }}",
            "spd_val_tpl": "{{ value_json.speed }}",
            "payload_on": "on",
            "payload_off": "off",
            "spds": ["low", "medium", "high", "off"],
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }

        mode_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}_mode",
            "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state",
            "value_template": f"{{{{ value_json.{self.sub_device}_mode }}}}",
            "icon": "mdi:play-circle-outline",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}_mode",
            "device": self.device_info,
        }

        speed_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}_speed",
            "state_topic": f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state",
            "value_template": f"{{{{ value_json.{self.sub_device}_speed }}}}",
            "icon": "mdi:speedometer",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}_speed",
            "device": self.device_info,
        }

        return [
            (fan_topic, json.dumps(fan_payload)),
            (mode_topic, json.dumps(mode_payload)),
            (speed_topic, json.dumps(speed_payload)),
        ]

    def get_subscribe_topics(self) -> list[str]:
        fan_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode"
        spd_cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed"
        mode_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_mode/config"
        speed_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_speed/config"
        return [fan_topic, command_topic, spd_cmd_t, mode_topic, speed_topic]

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

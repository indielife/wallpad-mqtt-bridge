import json

from wallpad.devices.packet_builder import PacketBuilder
from wallpad.devices.topic import TopicContext
from wallpad.panel.devices.base import PanelDevice
from wallpad.panel.devices.controller import SwitchController
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.kocom.constants import DEVICE_PLUG


class PlugController(SwitchController):
    """한 방의 콘센트 스위치들을 묶는 컨트롤러입니다."""


class Plug(PanelDevice):
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
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
            sw_version=sw_version,
            hw_info=hw_info,
            packet_builder=packet_builder,
            topics=topics,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        topic = self.topics.config_topic
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "command_topic": self.topics.command_topic,
            "state_topic": self.topics.state_topic,
            "value_template": f"{{{{ value_json.{self.sub_device} }}}}",
            "icon": "mdi:power-socket-eu",
            "payload_on": "on",
            "payload_off": "off",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(self.topics.state_topic, value)]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_PLUG, self.room, self.sub_device, payload)

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_type = "plug"

        value_hex = ""
        all_device = device_type + "0"
        for i in range(1, 9):
            sub_device = device_type + str(i)
            if target != sub_device:
                if target == all_device:
                    value_hex += "ff" if value == "on" and sub_device in room_state else "00"
                else:
                    if sub_device in room_state and room_state[sub_device].get("state") == "on":
                        value_hex += "ff"
                    else:
                        value_hex += "00"
            else:
                value_hex += "ff" if value == "on" else "00"

        if self.packet_builder:
            return self.packet_builder.encode(
                src=device_type,
                dst="wallpad",
                room=self.room,
                cmd=cmd,
                value_hex=value_hex,
            )
        return None

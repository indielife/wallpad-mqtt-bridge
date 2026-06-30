import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.panel.topic import TopicContext
from wallpad.protocol.kocom.constants import DEVICE_LIGHT, KOCOM_COMMAND_REV, KOCOM_DEVICE_REV


class Light(BaseDevice):
    def __init__(
        self,
        name_prefix: str,
        room: str,
        sub_device: str,
        sw_version: str,
        packet_builder: PacketBuilder | None = None,
        topics: TopicContext | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
            sw_version=sw_version,
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
            "payload_on": "on",
            "payload_off": "off",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(self.topics.state_topic, value)]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_LIGHT, self.room, self.sub_device, payload)

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        room_rev = kwargs.get("room_rev", {})

        device_type = "light"
        device_hex = KOCOM_DEVICE_REV.get(device_type, "0e")
        room_hex = room_rev.get(self.room, "00")
        dst_hex = KOCOM_DEVICE_REV.get("wallpad", "01") + room_rev.get("wallpad", "00")
        cmd_hex = KOCOM_COMMAND_REV.get(cmd, "00")

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
            return self.packet_builder.build(
                device_hex=device_hex,
                room_hex=room_hex,
                dst_hex=dst_hex,
                cmd_hex=cmd_hex,
                value_hex=value_hex,
            )
        return None

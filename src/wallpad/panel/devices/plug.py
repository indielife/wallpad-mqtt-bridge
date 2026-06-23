import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.mqtt import HA_PREFIX, HA_SWITCH
from wallpad.protocol.kocom.constants import DEVICE_PLUG


class Plug(BaseDevice):
    def __init__(
        self,
        name_prefix: str,
        room: str,
        sub_device: str,
        sw_version: str,
        packet_builder: PacketBuilder | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/config"
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "command_topic": f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set",
            "state_topic": f"{HA_PREFIX}/{HA_SWITCH}/{self.room}/state",
            "value_template": f"{{{{ value_json.{self.sub_device} }}}}",
            "icon": "mdi:power-socket-eu",
            "payload_on": "on",
            "payload_off": "off",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(f"{HA_PREFIX}/{HA_SWITCH}/{self.room}/state", value)]

    def get_subscribe_topics(self) -> list[str]:
        topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set"
        return [topic, command_topic]

    def get_command_topics(self) -> list[str]:
        return [f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set"]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_PLUG, self.room, self.sub_device, payload)

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_rev = kwargs.get("device_rev", {})
        room_rev = kwargs.get("room_rev", {})
        cmd_rev = kwargs.get("cmd_rev", {})

        device_type = "plug"
        device_hex = device_rev.get(device_type, "3b")
        room_hex = room_rev.get(self.room, "00")
        dst_hex = device_rev.get("wallpad", "01") + room_rev.get("wallpad", "00")
        cmd_hex = cmd_rev.get(cmd, "00")

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

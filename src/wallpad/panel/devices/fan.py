import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.devices.topic import TopicContext
from wallpad.protocol.kocom.constants import (
    DEVICE_FAN,
    KOCOM_COMMAND_REV,
    KOCOM_DEVICE_REV,
    KOCOM_FAN_SPEED_REV,
)


class Fan(BaseDevice):
    def __init__(
        self,
        name_prefix: str,
        sw_version: str,
        packet_builder: PacketBuilder | None = None,
        topics: TopicContext | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="fan",
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
            "command_topic": self.topics.mode_command_topic,
            "state_topic": self.topics.state_topic,
            "spd_cmd_t": self.topics.speed_command_topic,
            "spd_stat_t": self.topics.speed_state_topic,
            "state_value_template": "{{ value_json.mode }}",
            "spd_val_tpl": "{{ value_json.speed }}",
            "payload_on": "on",
            "payload_off": "off",
            "spds": ["low", "medium", "high", "off"],
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(self.topics.state_topic, value)]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_FAN, self.room, "", payload)

    def get_optimistic_state(self, device_states) -> dict | None:
        room_state = device_states[DEVICE_FAN][self.room]
        return {
            "mode": room_state["mode"]["set"],
            "speed": room_state["speed"]["set"],
        }

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        room_rev = kwargs.get("room_rev", {})

        device_hex = KOCOM_DEVICE_REV.get(self.sub_device, "48")
        room_hex = room_rev.get(self.room, "00")
        dst_hex = KOCOM_DEVICE_REV.get("wallpad", "01") + room_rev.get("wallpad", "00")
        cmd_hex = KOCOM_COMMAND_REV.get(cmd, "00")

        value_hex = ""
        try:
            mode = room_state.get("mode", {}).get("set", "off")
            speed = room_state.get("speed", {}).get("set", "off")
            if mode == "on":
                value_hex += "1100"
            elif mode == "off":
                value_hex += "0001"
            value_hex += KOCOM_FAN_SPEED_REV.get(speed, "0")
            value_hex += "00000000000"
        except Exception:
            return None

        if self.packet_builder:
            return self.packet_builder.build(
                device_hex=device_hex,
                room_hex=room_hex,
                dst_hex=dst_hex,
                cmd_hex=cmd_hex,
                value_hex=value_hex,
            )
        return None

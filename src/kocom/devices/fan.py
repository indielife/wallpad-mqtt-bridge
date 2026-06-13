import json

from .base import BaseDevice
from .packet_builder import PacketBuilder

HA_PREFIX = "homeassistant"
HA_FAN = "fan"


class Fan(BaseDevice):
    def __init__(
        self, name_prefix: str, sw_version: str, packet_builder: PacketBuilder | None = None
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="fan",
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "cmd_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode",
            "stat_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/state",
            "spd_cmd_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed",
            "spd_stat_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/state",
            "stat_val_tpl": "{{ value_json.mode }}",
            "spd_val_tpl": "{{ value_json.speed }}",
            "pl_on": "on",
            "pl_off": "off",
            "spds": ["low", "medium", "high", "off"],
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_subscribe_topics(self) -> list[str]:
        topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode"
        spd_cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed"
        return [topic, cmd_t, spd_cmd_t]

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_rev = kwargs.get("device_rev", {})
        room_rev = kwargs.get("room_rev", {})
        cmd_rev = kwargs.get("cmd_rev", {})
        fan_speed_rev = kwargs.get("fan_speed_rev", {})

        device_hex = device_rev.get(self.sub_device, "48")
        room_hex = room_rev.get(self.room, "00")
        dst_hex = device_rev.get("wallpad", "01") + room_rev.get("wallpad", "00")
        cmd_hex = cmd_rev.get(cmd, "00")

        value_hex = ""
        try:
            mode = room_state.get("mode", {}).get("set", "off")
            speed = room_state.get("speed", {}).get("set", "off")
            if mode == "on":
                value_hex += "1100"
            elif mode == "off":
                value_hex += "0001"
            value_hex += fan_speed_rev.get(speed, "0")
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

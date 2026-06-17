import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.mqtt import HA_LIGHT, HA_PREFIX


class Light(BaseDevice):
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
        topic = f"{HA_PREFIX}/{HA_LIGHT}/{self.room}_{self.sub_device}/config"
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "cmd_t": f"{HA_PREFIX}/{HA_LIGHT}/{self.room}_{self.sub_device}/set",
            "stat_t": f"{HA_PREFIX}/{HA_LIGHT}/{self.room}/state",
            "val_tpl": f"{{{{ value_json.{self.sub_device} }}}}",
            "pl_on": "on",
            "pl_off": "off",
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_subscribe_topics(self) -> list[str]:
        topic = f"{HA_PREFIX}/{HA_LIGHT}/{self.room}_{self.sub_device}/config"
        cmd_t = f"{HA_PREFIX}/{HA_LIGHT}/{self.room}_{self.sub_device}/set"
        return [topic, cmd_t]

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_rev = kwargs.get("device_rev", {})
        room_rev = kwargs.get("room_rev", {})
        cmd_rev = kwargs.get("cmd_rev", {})

        device_type = "light"
        device_hex = device_rev.get(device_type, "0e")
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

import json

from .base import BaseDevice

HA_PREFIX = "homeassistant"
HA_LIGHT = "light"


class Light(BaseDevice):
    def __init__(self, name_prefix: str, room: str, sub_device: str, sw_version: str):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
            sw_version=sw_version,
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

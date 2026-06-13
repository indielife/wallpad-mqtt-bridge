import json

from .base import BaseDevice

HA_PREFIX = "homeassistant"
HA_FAN = "fan"


class Fan(BaseDevice):
    def __init__(self, name_prefix: str, sw_version: str):
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="fan",
            sw_version=sw_version,
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

import json

from .base import BaseDevice

HA_PREFIX = "homeassistant"
HA_CLIMATE = "climate"


class Thermostat(BaseDevice):
    def __init__(self, name_prefix: str, room: str, sw_version: str):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device="thermostat",
            sw_version=sw_version,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        topic = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/config"
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "mode_cmd_t": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/mode",
            "mode_stat_t": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state",
            "mode_stat_tpl": "{{ value_json.mode }}",
            "temp_cmd_t": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/target_temp",
            "temp_stat_t": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state",
            "temp_stat_tpl": "{{ value_json.target_temp }}",
            "curr_temp_t": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state",
            "curr_temp_tpl": "{{ value_json.current_temp }}",
            "min_temp": 5,
            "max_temp": 40,
            "temp_step": 1,
            "modes": ["off", "heat", "fan_only"],
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_subscribe_topics(self) -> list[str]:
        topic = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/config"
        mode_cmd_t = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/mode"
        temp_cmd_t = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/target_temp"
        return [topic, mode_cmd_t, temp_cmd_t]

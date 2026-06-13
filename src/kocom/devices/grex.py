import json

from .base import BaseDevice

HA_PREFIX = "homeassistant"
HA_FAN = "fan"
HA_SENSOR = "sensor"


class GrexVentilator(BaseDevice):
    def __init__(self, name_prefix: str, sw_version: str):
        super().__init__(
            name_prefix=name_prefix,
            room="grex",
            sub_device="fan",
            sw_version=sw_version,
        )

    @property
    def device_info(self) -> dict:
        """Grex 고유의 기기 메타데이터를 반환하도록 오버라이딩합니다."""
        return {
            "name": "Grex Ventilator",
            "ids": "grex_ventilator",
            "mf": "Grex",
            "mdl": "Ventilator",
            "sw": self.sw_version,
        }

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        fan_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        mode_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_mode/config"
        speed_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_speed/config"

        if remove:
            return [(fan_topic, ""), (mode_topic, ""), (speed_topic, "")]

        fan_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}",
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

        mode_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}_mode",
            "stat_t": f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state",
            "val_tpl": f"{{{{ value_json.{self.sub_device}_mode }}}}",
            "ic": "mdi:play-circle-outline",
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}_mode",
            "device": self.device_info,
        }

        speed_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}_speed",
            "stat_t": f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state",
            "val_tpl": f"{{{{ value_json.{self.sub_device}_speed }}}}",
            "ic": "mdi:speedometer",
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}_speed",
            "device": self.device_info,
        }

        return [
            (fan_topic, json.dumps(fan_payload)),
            (mode_topic, json.dumps(mode_payload)),
            (speed_topic, json.dumps(speed_payload)),
        ]

    def get_subscribe_topics(self) -> list[str]:
        fan_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode"
        spd_cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed"
        mode_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_mode/config"
        speed_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_speed/config"
        return [fan_topic, cmd_t, spd_cmd_t, mode_topic, speed_topic]

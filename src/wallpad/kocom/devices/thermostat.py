import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.mqtt import HA_CLIMATE, HA_PREFIX


class Thermostat(BaseDevice):
    def __init__(
        self,
        name_prefix: str,
        room: str,
        sw_version: str,
        packet_builder: PacketBuilder | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device="thermostat",
            sw_version=sw_version,
            packet_builder=packet_builder,
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

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_rev = kwargs.get("device_rev", {})
        room_thermostat_rev = kwargs.get("room_thermostat_rev", {})
        cmd_rev = kwargs.get("cmd_rev", {})

        device_hex = device_rev.get(self.sub_device, "36")
        room_hex = room_thermostat_rev.get(self.room, "00")
        dst_hex = device_rev.get("wallpad", "01") + kwargs.get("room_rev", {}).get("wallpad", "00")
        cmd_hex = cmd_rev.get(cmd, "00")

        value_hex = ""
        try:
            mode = room_state.get("mode", {}).get("set", "off")
            target_temp = room_state.get("target_temp", {}).get("set", 22.0)
            if mode == "heat":
                value_hex += "1100"
            elif mode == "off":
                value_hex += "0100"
            else:
                value_hex += "1101"
            value_hex += f"{int(float(target_temp)):02x}"
            value_hex += "0000000000"
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

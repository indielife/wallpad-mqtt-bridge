import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.mqtt import HA_CLIMATE, HA_PREFIX
from wallpad.protocol.kocom.constants import DEVICE_THERMOSTAT


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
            "mode_command_topic": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/mode",
            "mode_state_topic": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state",
            "mode_state_template": "{{ value_json.mode }}",
            "temperature_command_topic": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/target_temp",
            "temperature_state_topic": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state",
            "temperature_state_template": "{{ value_json.target_temp }}",
            "current_temperature_topic": f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state",
            "current_temperature_template": "{{ value_json.current_temp }}",
            "min_temp": 5,
            "max_temp": 40,
            "temp_step": 1,
            "modes": ["off", "heat", "fan_only"],
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/state", value)]

    def get_subscribe_topics(self) -> list[str]:
        topic = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/config"
        mode_command_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/mode"
        temperature_command_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/target_temp"
        return [topic, mode_command_topic, temperature_command_topic]

    def get_command_topics(self) -> list[str]:
        return [
            f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/mode",
            f"{HA_PREFIX}/{HA_CLIMATE}/{self.room}/target_temp",
        ]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_THERMOSTAT, self.room, "", payload)

    def get_optimistic_state(self, device_states) -> dict | None:
        room_state = device_states[DEVICE_THERMOSTAT][self.room]
        return {
            "mode": room_state["mode"]["set"],
            "target_temp": room_state["target_temp"]["set"],
            "current_temp": room_state["current_temp"]["state"],
        }

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

import json

from wallpad.apps.panel.devices.base import PanelDevice
from wallpad.apps.panel.devices.controller import CategoryController
from wallpad.devices.topic import TopicContext
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.kocom.constants import DEVICE_THERMOSTAT


class ThermostatController(CategoryController):
    """온도조절기 컨트롤러입니다. 목표온도 설정은 자동으로 heat 모드를 동반합니다."""

    def apply_ha_command(
        self, sub_device: str, command: str, payload: str, default_speed: str
    ) -> None:
        state = self.state
        if command != "mode":
            state["target_temp"].set = int(float(payload))
            state["mode"].set = "heat"
            state["target_temp"].last = "set"
            state["mode"].last = "set"
        else:
            state["mode"].set = payload
            state["mode"].last = "set"

    def reflect_rs485(self, value, default_speed: str) -> None:
        state = self.state
        for sub, v in value.items():
            sub_state = state[sub]
            if sub == "mode":
                sub_state.state = v
            else:
                sub_state.state = int(float(v))
                state["mode"].state = "heat"
            self.recover_if_confirmed(sub_state)

    def make_packet(self, cmd: str, target: str, value: str) -> str | None:
        value_hex = ""
        try:
            mode = self.state.get("mode", {}).get("set", "off")
            target_temp = self.state.get("target_temp", {}).get("set", 22.0)
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
            return self.packet_builder.encode(
                src=self.category,
                dst="wallpad",
                room=self.room,
                cmd=cmd,
                value_hex=value_hex,
            )
        return None


class Thermostat(PanelDevice):
    def __init__(
        self,
        name_prefix: str,
        room: str,
        sw_version: str,
        hw_info: HardwareInfo,
        topics: TopicContext | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device="thermostat",
            sw_version=sw_version,
            hw_info=hw_info,
            topics=topics,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        topic = self.topics.config_topic
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "mode_command_topic": self.topics.mode_command_topic,
            "mode_state_topic": self.topics.mode_state_topic,
            "mode_state_template": "{{ value_json.mode }}",
            "temperature_command_topic": self.topics.temperature_command_topic,
            "temperature_state_topic": self.topics.temperature_state_topic,
            "temperature_state_template": "{{ value_json.target_temp }}",
            "current_temperature_topic": self.topics.current_temperature_topic,
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
        return [(self.topics.state_topic, value)]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_THERMOSTAT, self.room, "", payload)

    def get_optimistic_state(self, device_states) -> dict | None:
        room_state = device_states[DEVICE_THERMOSTAT][self.room]
        return {
            "mode": room_state["mode"]["set"],
            "target_temp": room_state["target_temp"]["set"],
            "current_temp": room_state["current_temp"]["state"],
        }

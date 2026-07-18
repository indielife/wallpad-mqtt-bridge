import json

from wallpad.devices.packet_builder import PacketBuilder
from wallpad.devices.topic import TopicContext
from wallpad.panel.devices.base import PanelDevice
from wallpad.panel.devices.controller import CategoryController
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.kocom.constants import DEVICE_FAN, KOCOM_HEX_BY_FAN_SPEED


class FanController(CategoryController):
    """환기팬 컨트롤러입니다. mode와 speed가 상호 결합된 상태를 함께 관리합니다."""

    def apply_ha_command(
        self, sub_device: str, command: str, payload: str, default_speed: str
    ) -> None:
        state = self.state
        if command != "mode":
            state["speed"].set = payload
            state["mode"].set = "on"
        else:
            state["speed"].set = default_speed if payload == "on" else "off"
            state["mode"].set = payload
        state["speed"].last = "set"
        state["mode"].last = "set"

    def reflect_rs485(self, value, default_speed: str) -> None:
        state = self.state
        for sub, v in value.items():
            sub_state = state[sub]
            if sub == "mode":
                sub_state.state = v
                state["speed"].state = "off" if v == "off" else default_speed
            else:
                sub_state.state = v
                state["mode"].state = "off" if v == "off" else "on"
            self.recover_if_confirmed(sub_state)

    def build_packet(self, cmd: str, target: str, value: str) -> str | None:

        value_hex = ""
        try:
            mode = self.state.get("mode", {}).get("set", "off")
            speed = self.state.get("speed", {}).get("set", "off")
            if mode == "on":
                value_hex += "1100"
            elif mode == "off":
                value_hex += "0001"
            value_hex += KOCOM_HEX_BY_FAN_SPEED.get(speed, "0")
            value_hex += "00000000000"
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


class Fan(PanelDevice):
    def __init__(
        self,
        name_prefix: str,
        sw_version: str,
        hw_info: HardwareInfo,
        topics: TopicContext | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="fan",
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

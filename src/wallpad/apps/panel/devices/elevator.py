import json

from wallpad.apps.panel.devices.base import PanelDevice
from wallpad.apps.panel.devices.controller import CategoryController
from wallpad.devices.topic import TopicContext
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.kocom.constants import DEVICE_ELEVATOR


class ElevatorController(CategoryController):
    """엘리베이터 호출 컨트롤러입니다. off 명령은 RS485 ack 없이 즉시 확정됩니다."""

    def apply_ha_command(
        self, sub_device: str, command: str, payload: str, default_speed: str
    ) -> None:
        sub_state = self.state[sub_device]
        sub_state.set = payload
        sub_state.last = "state" if payload == "off" else command

    def reflect_rs485(self, value, default_speed: str) -> None:
        sub_state = self.state[self.category]
        sub_state.state = value
        sub_state.last = "state"
        sub_state.count = 0

    def make_packet(self, cmd: str, target: str, value: str) -> str | None:
        value_hex = "0000000000000000"

        if self.packet_builder:
            return self.packet_builder.encode(
                src="wallpad",
                dst="elevator",
                room=self.room,
                cmd="on",
                value_hex=value_hex,
            )
        return None


class Elevator(PanelDevice):
    def __init__(
        self,
        name_prefix: str,
        sw_version: str,
        hw_info: HardwareInfo,
        topics: TopicContext | None = None,
    ):
        # 엘리베이터는 기본적으로 'wallpad' 방에 종속된 'elevator' 장치입니다.
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="elevator",
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
            "command_topic": self.topics.command_topic,
            "state_topic": self.topics.state_topic,
            "value_template": f"{{{{ value_json.{self.sub_device} }}}}",
            "icon": "mdi:elevator",
            "payload_on": "on",
            "payload_off": "off",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(self.topics.state_topic, {self.sub_device: value})]

    def resolve_command(self, command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_ELEVATOR, self.room, self.sub_device, payload)

    def get_optimistic_state(self, device_states) -> object | None:
        # "off" 명령은 RS485 ack가 없으므로 즉시 publish
        set_val = device_states[DEVICE_ELEVATOR][self.room][self.sub_device]["set"]
        return set_val if set_val == "off" else None

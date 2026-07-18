import json

from wallpad.devices.topic import TopicContext
from wallpad.panel.devices.base import PanelDevice
from wallpad.panel.devices.controller import SwitchController
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.kocom.constants import DEVICE_PLUG


class PlugController(SwitchController):
    """한 방의 콘센트 스위치들을 묶는 컨트롤러입니다."""


class Plug(PanelDevice):
    def __init__(
        self,
        name_prefix: str,
        room: str,
        sub_device: str,
        sw_version: str,
        hw_info: HardwareInfo,
        topics: TopicContext | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
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
            "icon": "mdi:power-socket-eu",
            "payload_on": "on",
            "payload_off": "off",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(self.topics.state_topic, value)]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_PLUG, self.room, self.sub_device, payload)

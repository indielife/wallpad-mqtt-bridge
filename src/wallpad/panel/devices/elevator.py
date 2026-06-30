import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.panel.topic import TopicContext
from wallpad.protocol.kocom.constants import DEVICE_ELEVATOR, KOCOM_COMMAND_REV, KOCOM_DEVICE_REV


class Elevator(BaseDevice):
    def __init__(
        self,
        name_prefix: str,
        sw_version: str,
        packet_builder: PacketBuilder | None = None,
        topics: TopicContext | None = None,
    ):
        # 엘리베이터는 기본적으로 'wallpad' 방에 종속된 'elevator' 장치입니다.
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="elevator",
            sw_version=sw_version,
            packet_builder=packet_builder,
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

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        return (DEVICE_ELEVATOR, self.room, self.sub_device, payload)

    def get_optimistic_state(self, device_states) -> object | None:
        # "off" 명령은 RS485 ack가 없으므로 즉시 publish
        set_val = device_states[DEVICE_ELEVATOR][self.room][self.sub_device]["set"]
        return set_val if set_val == "off" else None

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        room_rev = kwargs.get("room_rev", {})

        device_hex = KOCOM_DEVICE_REV.get("wallpad", "01")
        room_hex = room_rev.get("wallpad", "00")
        dst_hex = KOCOM_DEVICE_REV.get("elevator", "44") + room_rev.get("wallpad", "00")
        cmd_hex = KOCOM_COMMAND_REV.get("on", "01")
        value_hex = "0000000000000000"

        if self.packet_builder:
            return self.packet_builder.build(
                device_hex=device_hex,
                room_hex=room_hex,
                dst_hex=dst_hex,
                cmd_hex=cmd_hex,
                value_hex=value_hex,
            )
        return None

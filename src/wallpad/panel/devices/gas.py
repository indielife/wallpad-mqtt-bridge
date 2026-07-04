import json
import logging

from wallpad.devices.packet_builder import PacketBuilder
from wallpad.devices.topic import TopicContext
from wallpad.panel.devices.base import PanelDevice
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.kocom.constants import DEVICE_GAS

logger = logging.getLogger(__name__)


class Gas(PanelDevice):
    def __init__(
        self,
        name_prefix: str,
        sw_version: str,
        hw_info: HardwareInfo,
        packet_builder: PacketBuilder | None = None,
        topics: TopicContext | None = None,
    ):
        # 가스 밸브도 엘리베이터처럼 'wallpad' 방에 종속된 'gas' 장치입니다.
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="gas",
            sw_version=sw_version,
            hw_info=hw_info,
            packet_builder=packet_builder,
            topics=topics,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        switch_topic = self.topics.switch_config_topic
        sensor_topic = self.topics.sensor_config_topic

        if remove:
            return [(switch_topic, ""), (sensor_topic, "")]

        switch_payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "command_topic": self.topics.command_topic,
            "state_topic": self.topics.switch_state_topic,
            "value_template": f"{{{{ value_json.{self.sub_device} }}}}",
            "icon": "mdi:gas-cylinder",
            "payload_on": "on",
            "payload_off": "off",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }

        # TODO: HA 기기 식별자(uniq_id) 중복 분리 필요
        # HA 원칙상 물리적 기기 하나에 달린 여러 기능(Entity)들은 서로 다른 uniq_id를 가져야 하나,
        # 기존 레거시 코드에서 스위치와 센서가 완전히 동일한 uniq_id({name}_wallpad_gas)를
        # 사용하고 있었습니다. 기존 사용자들의 HA 설정이 깨지는 것을 막기 위해 하위 호환성을
        # 유지 중이며, 추후 메이저 업데이트 시 _switch, _sensor 접미사를 붙여 수정해야 합니다.
        sensor_payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "state_topic": self.topics.sensor_state_topic,
            "value_template": f"{{{{ value_json.{self.sub_device} }}}}",
            "icon": "mdi:gas-cylinder",
            # TODO: 동일 ID 사용 중 (수정 필요)
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [
            (switch_topic, json.dumps(switch_payload)),
            (sensor_topic, json.dumps(sensor_payload)),
        ]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        data = {self.sub_device: value}
        return [
            (self.topics.sensor_state_topic, data),
            (self.topics.switch_state_topic, data),
        ]

    def resolve_command(self, _command: str, payload: str) -> tuple[str, str, str, str] | None:
        if payload == "on":
            logger.warning("Cannot set GAS to ON from HA")
            return None
        return (DEVICE_GAS, self.room, self.sub_device, payload)

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        value_hex = "0000000000000000"

        if self.packet_builder:
            return self.packet_builder.encode(
                src=self.sub_device,
                dst="wallpad",
                room=self.room,
                cmd="off",
                value_hex=value_hex,
            )
        return None

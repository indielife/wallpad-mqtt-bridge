import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.mqtt import HA_PREFIX, HA_SENSOR, HA_SWITCH


class Gas(BaseDevice):
    def __init__(
        self, name_prefix: str, sw_version: str, packet_builder: PacketBuilder | None = None
    ):
        # 가스 밸브도 엘리베이터처럼 'wallpad' 방에 종속된 'gas' 장치입니다.
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="gas",
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        switch_topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/config"
        sensor_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/config"

        if remove:
            return [(switch_topic, ""), (sensor_topic, "")]

        switch_payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "cmd_t": f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set",
            "stat_t": f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/state",
            "val_tpl": f"{{{{ value_json.{self.sub_device} }}}}",
            "ic": "mdi:gas-cylinder",
            "pl_on": "on",
            "pl_off": "off",
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }

        # TODO: HA 기기 식별자(uniq_id) 중복 분리 필요
        # HA 원칙상 물리적 기기 하나에 달린 여러 기능(Entity)들은 서로 다른 uniq_id를 가져야 하나,
        # 기존 레거시 코드에서 스위치와 센서가 완전히 동일한 uniq_id({name}_wallpad_gas)를
        # 사용하고 있었습니다. 기존 사용자들의 HA 설정이 깨지는 것을 막기 위해 하위 호환성을
        # 유지 중이며, 추후 메이저 업데이트 시 _switch, _sensor 접미사를 붙여 수정해야 합니다.
        sensor_payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "stat_t": f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state",
            "val_tpl": f"{{{{ value_json.{self.sub_device} }}}}",
            "ic": "mdi:gas-cylinder",
            # TODO: 동일 ID 사용 중 (수정 필요)
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [
            (switch_topic, json.dumps(switch_payload)),
            (sensor_topic, json.dumps(sensor_payload)),
        ]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        data = {self.sub_device: value}
        return [
            (f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state", data),
            (f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/state", data),
        ]

    def get_subscribe_topics(self) -> list[str]:
        switch_topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/config"
        cmd_t = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set"
        sensor_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/config"
        return [switch_topic, cmd_t, sensor_topic]

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_rev = kwargs.get("device_rev", {})
        room_rev = kwargs.get("room_rev", {})
        cmd_rev = kwargs.get("cmd_rev", {})

        device_hex = device_rev.get(self.sub_device, "2c")
        room_hex = room_rev.get(self.room, "00")
        dst_hex = device_rev.get("wallpad", "01") + room_rev.get("wallpad", "00")
        cmd_hex = cmd_rev.get("off", "02")
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

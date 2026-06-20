import json

from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.mqtt import HA_PREFIX, HA_SWITCH


class Elevator(BaseDevice):
    def __init__(
        self, name_prefix: str, sw_version: str, packet_builder: PacketBuilder | None = None
    ):
        # 엘리베이터는 기본적으로 'wallpad' 방에 종속된 'elevator' 장치입니다.
        super().__init__(
            name_prefix=name_prefix,
            room="wallpad",
            sub_device="elevator",
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/config"
        if remove:
            return [(topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "cmd_t": f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set",
            "stat_t": f"{HA_PREFIX}/{HA_SWITCH}/{self.room}/state",
            "val_tpl": f"{{{{ value_json.{self.sub_device} }}}}",
            "ic": "mdi:elevator",
            "pl_on": "on",
            "pl_off": "off",
            "uniq_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(topic, json.dumps(payload))]

    def get_ha_state_messages(self, value) -> list[tuple[str, dict]]:
        return [(f"{HA_PREFIX}/{HA_SWITCH}/{self.room}/state", {self.sub_device: value})]

    def get_subscribe_topics(self) -> list[str]:
        topic = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/config"
        cmd_t = f"{HA_PREFIX}/{HA_SWITCH}/{self.room}_{self.sub_device}/set"
        return [topic, cmd_t]

    def build_packet(
        self, cmd: str, target: str, value: str, room_state: dict, **kwargs
    ) -> str | None:
        device_rev = kwargs.get("device_rev", {})
        room_rev = kwargs.get("room_rev", {})
        cmd_rev = kwargs.get("cmd_rev", {})

        device_hex = device_rev.get("wallpad", "01")
        room_hex = room_rev.get("wallpad", "00")
        dst_hex = device_rev.get("elevator", "44") + room_rev.get("wallpad", "00")
        cmd_hex = cmd_rev.get("on", "01")
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

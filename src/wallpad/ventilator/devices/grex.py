import json
from typing import ClassVar

from wallpad.devices.base import BaseDevice
from wallpad.mqtt import HA_FAN, HA_PREFIX, HA_SENSOR
from wallpad.protocol.grex.constants import MODE_HEX_MAP, SPEED_HEX_MAP
from wallpad.protocol.grex.packet_builder import GrexPacketBuilder


class GrexDevice(BaseDevice):
    """Grex 환기장치 기기들이 공유하는 식별자·메타데이터 기반 클래스입니다."""

    def __init__(
        self,
        sw_version: str,
        name_prefix: str = "grex",
        packet_builder: GrexPacketBuilder | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="grex",
            sub_device="fan",
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    @property
    def device_info(self) -> dict:
        """Grex 고유의 기기 메타데이터를 반환하도록 오버라이딩합니다."""
        return {
            "name": "Grex Ventilator",
            "identifiers": "grex_ventilator",
            "manufacturer": "Grex",
            "model": "Ventilator",
            "sw_version": self.sw_version,
        }


class GrexVentilatorUnit(GrexDevice):
    """HA fan 도메인을 담당하는 환기장치 본체입니다."""

    MODE_HEX_MAP: ClassVar[dict[str, str]] = MODE_HEX_MAP
    SPEED_HEX_MAP: ClassVar[dict[str, str]] = SPEED_HEX_MAP

    @property
    def state_topic(self) -> str:
        """HA fan 엔티티의 상태 토픽입니다."""
        return f"{HA_PREFIX}/{HA_FAN}/{self.room}/state"

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        config_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        if remove:
            return [(config_topic, "")]

        payload = {
            "name": f"{self.name_prefix}_{self.sub_device}",
            "command_topic": f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode",
            "state_topic": self.state_topic,
            "spd_cmd_t": f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed",
            "spd_stat_t": self.state_topic,
            "state_value_template": "{{ value_json.mode }}",
            "spd_val_tpl": "{{ value_json.speed }}",
            "payload_on": "on",
            "payload_off": "off",
            "spds": ["low", "medium", "high", "off"],
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}",
            "device": self.device_info,
        }
        return [(config_topic, json.dumps(payload))]

    def get_subscribe_topics(self) -> list[str]:
        config_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}_{self.sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_FAN}/{self.room}/mode"
        spd_cmd_t = f"{HA_PREFIX}/{HA_FAN}/{self.room}/speed"
        return [config_topic, command_topic, spd_cmd_t]

    def build_control_packet(self, mode: str, speed: str) -> str:
        """환기장치 본체를 제어하기 위한 패킷을 생성합니다."""
        if not self.packet_builder:
            return ""

        mode_hex = self.MODE_HEX_MAP.get(mode)
        speed_hex = self.SPEED_HEX_MAP.get(speed)

        if not mode_hex or not speed_hex:
            return ""

        if ((mode == "auto" or mode == "sleep") and (speed == "off")) or (
            speed in ["low", "medium", "high"]
        ):
            postfix_hex = "0001"
        else:
            postfix_hex = "0000"

        return self.packet_builder.build_control(mode_hex, speed_hex, postfix_hex)

    def build_response_packet(self, mode: str, speed: str) -> str:
        """월패드 컨트롤러에 상태를 동기화하기 위한 응답 패킷을 생성합니다."""
        if not self.packet_builder:
            return ""

        speed_hex = self.SPEED_HEX_MAP.get(speed, "0000")
        postfix_hex = "0000000100" if speed in ["low", "medium", "high"] else "0000000000"

        return self.packet_builder.build_response(speed_hex, postfix_hex)


class GrexVentilatorController(GrexDevice):
    """HA sensor 도메인(모드/속도 표시)을 담당하는 조작·표시기입니다."""

    @property
    def state_topic(self) -> str:
        """HA sensor 엔티티의 상태 토픽입니다."""
        return f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}/state"

    def get_discovery_payloads(self, remove: bool = False) -> list[tuple[str, str]]:
        mode_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_mode/config"
        speed_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_speed/config"

        if remove:
            return [(mode_topic, ""), (speed_topic, "")]

        mode_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}_mode",
            "state_topic": self.state_topic,
            "value_template": f"{{{{ value_json.{self.sub_device}_mode }}}}",
            "icon": "mdi:play-circle-outline",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}_mode",
            "device": self.device_info,
        }

        speed_payload = {
            "name": f"{self.name_prefix}_{self.sub_device}_speed",
            "state_topic": self.state_topic,
            "value_template": f"{{{{ value_json.{self.sub_device}_speed }}}}",
            "icon": "mdi:speedometer",
            "unique_id": f"{self.name_prefix}_{self.room}_{self.sub_device}_speed",
            "device": self.device_info,
        }

        return [
            (mode_topic, json.dumps(mode_payload)),
            (speed_topic, json.dumps(speed_payload)),
        ]

    def get_subscribe_topics(self) -> list[str]:
        mode_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_mode/config"
        speed_topic = f"{HA_PREFIX}/{HA_SENSOR}/{self.room}_{self.sub_device}_speed/config"
        return [mode_topic, speed_topic]

    def build_sensor_payload(self, mode: str, speed: str, *, ha_mode_on: bool) -> dict:
        """모드/속도를 HA sensor 표시용 한글 페이로드로 변환합니다.

        ha_mode_on은 mode가 off라도 HA에서 켠 상태(desired mode == "on")를
        표시로 반영하기 위한 플래그입니다.
        """
        payload = {"fan_mode": "off", "fan_speed": "off"}
        if mode != "off" or ha_mode_on:
            if mode == "auto":
                payload["fan_mode"] = "자동"
            elif mode == "manual":
                payload["fan_mode"] = "수동"
            elif mode == "sleep":
                payload["fan_mode"] = "취침"
            elif mode == "off" and ha_mode_on:
                payload["fan_mode"] = "HA"
            if speed == "low":
                payload["fan_speed"] = "1단"
            elif speed == "medium":
                payload["fan_speed"] = "2단"
            elif speed == "high":
                payload["fan_speed"] = "3단"
            elif speed == "off":
                payload["fan_speed"] = "대기"
        return payload

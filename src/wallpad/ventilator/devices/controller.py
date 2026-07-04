import json

from wallpad.mqtt import HA_PREFIX, HA_SENSOR
from wallpad.ventilator.devices.base import VentilatorDevice


class VentilatorController(VentilatorDevice):
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

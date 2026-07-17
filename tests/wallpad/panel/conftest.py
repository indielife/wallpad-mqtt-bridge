"""E2E 블랙박스 특성화 테스트용 페이크와 픽스처.

내부 상태(`device_states`/`devices`)가 아니라 Panel의 외부 경계
(RS485 `transport`, `MqttClient`)만 모킹해, 계층 구조 리팩토링 전후로
살아남는 회귀 안전망을 제공한다.
"""

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from wallpad.panel.panel import Panel


class FakeMqtt:
    """Panel이 사용하는 MqttClient 표면만 흉내내는 페이크.

    브로커 없이 발행(publish/publish_json)을 기록하고, 등록된 토픽 콜백으로
    수신 메시지를 전달(deliver)해 HA→브릿지 명령 경로를 재현한다.
    """

    def __init__(self):
        self.connect_callbacks = []
        self.topic_callbacks = []  # list[(pattern, regex, cb)]
        self.published = []  # list[(topic, payload, retain)]
        self.published_json = []  # list[(topic, data, retain)]

    def register_connect_callback(self, cb):
        self.connect_callbacks.append(cb)

    def register_topic_callback(self, pattern, cb):
        self.topic_callbacks.append((pattern, self._compile(pattern), cb))

    def publish(self, topic, payload, retain=True):
        self.published.append((topic, payload, retain))

    def publish_json(self, topic, data, retain=True):
        self.published_json.append((topic, data, retain))

    def deliver(self, topic, payload):
        """브로커가 매칭 토픽 메시지를 전달한 것처럼 등록 콜백을 호출한다."""
        for _pattern, regex, cb in self.topic_callbacks:
            if regex.match(topic):
                cb(topic, payload)

    @staticmethod
    def _compile(pattern: str) -> re.Pattern:
        parts = []
        for seg in pattern.split("/"):
            if seg == "#":
                parts.append(".*")
            elif seg == "+":
                parts.append("[^/]+")
            else:
                parts.append(re.escape(seg))
        return re.compile("^" + "/".join(parts) + "$")

    # --- 조회 편의 헬퍼 ---

    def json_topics(self) -> list[str]:
        return [topic for topic, _data, _retain in self.published_json]

    def json_for(self, topic: str) -> list:
        return [data for t, data, _retain in self.published_json if t == topic]


def _fake_transport() -> AsyncMock:
    transport = AsyncMock()
    transport.write_if_idle.return_value = True
    transport.is_idle = MagicMock(return_value=True)
    return transport


@pytest.fixture
def e2e_panel(mock_config):
    """단일 방(livingroom) + 집 단위 기기(fan/gas/elevator) 활성 E2E 패널.

    반환: (panel, fake_mqtt, transport)
    """
    mqtt = FakeMqtt()
    transport = _fake_transport()
    panel = Panel(mock_config, mqtt, transport)
    panel.ha_ready.set()
    return panel, mqtt, transport


def _make_room(name, room_no=None, light_count=0, plug_count=0, thermo_no=None):
    room = MagicMock()
    room.name = name
    room.room_no = room_no
    room.light_count = light_count
    room.plug_count = plug_count
    room.thermo_no = thermo_no
    room.light_addr = f"{room_no:02d}" if room_no is not None else None
    room.thermo_addr = f"{thermo_no:02d}" if thermo_no is not None else None
    return room


@pytest.fixture
def mock_config_multiroom():
    """두 방(livingroom/bedroom) 구성. 라우팅 격리 검증용.

    집 단위 기기(fan/gas/elevator)는 비활성화해 방 기기 발행/쓰기만 남긴다.
    """
    config = MagicMock()
    config.sw_version = "0.1.0"
    config.wallpad_manufacturer = "kocom"
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.kocom_default_speed = "low"

    config.rooms = [
        _make_room("livingroom", room_no=0, light_count=3, plug_count=2, thermo_no=0),
        _make_room("bedroom", room_no=1, light_count=2, plug_count=2, thermo_no=1),
    ]

    config.fan_enabled = False
    config.gas_enabled = False
    config.elevator_enabled = False

    config.kocom_room_rev = {"livingroom": "00", "bedroom": "01", "wallpad": "00"}
    config.kocom_room_thermostat_rev = {"livingroom": "00", "bedroom": "01"}
    config.kocom_room = {"00": "livingroom", "01": "bedroom"}
    config.kocom_room_thermostat = {"00": "livingroom", "01": "bedroom"}
    config.kocom_light_size = {"livingroom": 3, "bedroom": 2}
    config.kocom_plug_size = {"livingroom": 2, "bedroom": 2}
    return config


@pytest.fixture
def e2e_panel_multiroom(mock_config_multiroom):
    """두 방 구성 E2E 패널. 반환: (panel, fake_mqtt, transport)"""
    mqtt = FakeMqtt()
    transport = _fake_transport()
    panel = Panel(mock_config_multiroom, mqtt, transport)
    panel.ha_ready.set()
    return panel, mqtt, transport

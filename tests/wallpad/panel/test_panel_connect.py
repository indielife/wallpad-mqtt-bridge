"""
on_connect 메커니즘 및 race condition regression 테스트.

MQTT on_connect → _subscribe_ha_topics / _publish_ha_discovery →
ha_registry 설정 → retained 메시지 수신 → ha_ready.set() 흐름을 검증한다.
"""

from unittest.mock import MagicMock

import pytest

from wallpad.panel.panel import WallpadPanel


class EarlyFiringMqttClient:
    """connect() 호출 시 그 시점에 등록된 콜백만 즉시 발화.

    paho의 네트워크 스레드가 broker에 빠르게 연결되어 on_connect를
    register_connect_callback 이전에 발화하는 상황을 결정론적으로 시뮬레이션한다.
    """

    def __init__(self):
        self._connect_callbacks = []
        self.subscribed = []
        self.published = []

    def register_connect_callback(self, cb):
        self._connect_callbacks.append(cb)

    def register_message_callback(self, cb):
        pass

    def connect(self):
        for cb in list(self._connect_callbacks):
            cb()

    def subscribe(self, topic_list):
        self.subscribed.extend(t for t, _ in topic_list)

    def publish(self, topic, payload, **kwargs):
        self.published.append(topic)

    def publish_json(self, topic, payload, **kwargs):
        pass


# ---------------------------------------------------------------------------
# on_connect 정상 동작
# ---------------------------------------------------------------------------


def test_on_connect_publishes_discovery_and_sets_ha_registry(mock_config):
    """on_connect 호출 후 ha_registry가 마지막 config 토픽으로 설정되는지 검증."""
    mqtt = EarlyFiringMqttClient()
    panel = WallpadPanel(mock_config, mqtt, MagicMock())

    assert panel.ha_registry is False

    panel.on_connect(None, None, None)

    assert panel.ha_registry is not False
    assert isinstance(panel.ha_registry, str)
    assert panel.ha_registry.endswith("/config")


def test_on_connect_subscribes_to_config_and_command_topics(mock_config):
    """on_connect 후 config 토픽과 command 토픽이 모두 구독되는지 검증."""
    mqtt = EarlyFiringMqttClient()
    panel = WallpadPanel(mock_config, mqtt, MagicMock())

    panel.on_connect(None, None, None)

    config_topics = [t for t in mqtt.subscribed if t.endswith("/config")]
    command_topics = [t for t in mqtt.subscribed if t.endswith("/set")]
    assert len(config_topics) > 0
    assert len(command_topics) > 0


# ---------------------------------------------------------------------------
# ha_ready 게이트 메커니즘
# ---------------------------------------------------------------------------


def _make_sync_loop():
    """call_soon_threadsafe를 동기적으로 즉시 실행하는 루프 mock."""
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = lambda f: f()
    return loop


def test_ha_ready_set_after_retained_config_message(mock_config):
    """on_connect 이후 retained config 메시지를 수신하면 ha_ready가 설정되는지 검증."""
    mqtt = EarlyFiringMqttClient()
    panel = WallpadPanel(mock_config, mqtt, MagicMock())
    panel._loop = _make_sync_loop()

    panel.on_connect(None, None, None)
    assert not panel.ha_ready.is_set()  # 아직 준비 안 됨
    assert panel.ha_registry is not False

    # broker가 retained 메시지를 돌려주는 상황 시뮬레이션
    msg = MagicMock()
    msg.topic = panel.ha_registry
    msg.payload = b"{}"
    panel.on_message(None, None, msg)

    assert panel.ha_ready.is_set()


def test_ha_ready_not_set_if_wrong_topic_arrives(mock_config):
    """ha_registry와 다른 토픽이 오면 ha_ready가 설정되지 않아야 한다."""
    mqtt = EarlyFiringMqttClient()
    panel = WallpadPanel(mock_config, mqtt, MagicMock())
    panel._loop = _make_sync_loop()

    panel.on_connect(None, None, None)

    msg = MagicMock()
    msg.topic = "homeassistant/light/livingroom_light0/config"  # ha_registry가 아닌 토픽
    msg.payload = b"{}"
    panel.on_message(None, None, msg)

    # ha_registry(마지막 config 토픽)가 아닌 메시지로는 해제 안 됨
    if panel.ha_registry != msg.topic:
        assert not panel.ha_ready.is_set()


# ---------------------------------------------------------------------------
# Race condition regression
# ---------------------------------------------------------------------------


def test_connect_before_panel_init_prevents_on_connect(mock_config):
    """Regression: connect()를 패널 초기화 이전에 호출하면 on_connect가 발화하지 않는다."""
    mqtt = EarlyFiringMqttClient()

    # BUG 재현: connect()를 패널 생성 이전에 호출 (콜백 미등록 상태)
    mqtt.connect()

    panel = WallpadPanel(mock_config, mqtt, MagicMock())

    # on_connect가 발화하지 않았으므로 discovery 미발행 → ha_registry 미설정
    assert panel.ha_registry is False
    # ha_ready 미설정 — HA 명령이 모두 무시됨
    assert not panel.ha_ready.is_set()


def test_connect_after_panel_init_enables_scan(mock_config):
    """Fix 검증: connect()를 패널 초기화 이후에 호출하면 on_connect가 정상 발화한다."""
    mqtt = EarlyFiringMqttClient()

    panel = WallpadPanel(mock_config, mqtt, MagicMock())  # 콜백 등록 완료
    panel._loop = _make_sync_loop()
    mqtt.connect()  # 이제 on_connect 발화 → discovery 발행

    assert panel.ha_registry is not False

    # retained 메시지 도착 → ha_ready 설정
    msg = MagicMock()
    msg.topic = panel.ha_registry
    msg.payload = b"{}"
    panel.on_message(None, None, msg)

    assert panel.ha_ready.is_set()

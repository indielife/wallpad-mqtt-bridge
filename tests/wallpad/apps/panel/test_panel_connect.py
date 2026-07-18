"""
on_connect 메커니즘 및 race condition regression 테스트.

Panel 생성 시 register_topic_callback으로 토픽이 등록되고, MqttClient의
연결(on_connect) 시점에 자동 구독 → _publish_ha_discovery → ha_registry 설정 →
retained 메시지 수신 → ha_ready.set() 흐름을 검증한다.

실제 MqttClient(paho 클라이언트만 patch)를 사용해 라우팅 매칭 로직을
테스트에서 중복 구현하지 않는다.
"""

from unittest.mock import MagicMock, patch

import pytest

from wallpad.apps.panel.panel import Panel
from wallpad.mqtt import MqttClient, MqttConfig


@pytest.fixture
def mqtt_client():
    config = MqttConfig(host="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client"):
        yield MqttClient(config)


def _fire_connect(mqtt_client):
    mqtt_client._on_connect(mqtt_client.client, None, {}, 0)


def _dispatch(mqtt_client, topic, payload=""):
    msg = MagicMock()
    msg.topic = topic
    msg.payload = payload.encode()
    mqtt_client._on_message(mqtt_client.client, None, msg)


def _make_sync_loop():
    """call_soon_threadsafe를 동기적으로 즉시 실행하는 루프 mock."""
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = lambda f: f()
    return loop


# ---------------------------------------------------------------------------
# on_connect 정상 동작
# ---------------------------------------------------------------------------


def test_on_connect_publishes_discovery_and_sets_ha_registry(mock_config, mqtt_client):
    """on_connect 호출 후 ha_registry가 마지막 config 토픽으로 설정되는지 검증."""
    panel = Panel(mock_config, mqtt_client, MagicMock())

    assert panel.ha_registry is False

    _fire_connect(mqtt_client)

    assert panel.ha_registry is not False
    assert isinstance(panel.ha_registry, str)
    assert panel.ha_registry.endswith("/config")


def test_on_connect_subscribes_to_config_and_command_topics(mock_config, mqtt_client):
    """Panel 생성 후 config 토픽과 command 토픽이 모두 라우터에 등록되는지 검증."""
    Panel(mock_config, mqtt_client, MagicMock())

    registered_topics = [pattern for pattern, _, _ in mqtt_client._topic_callbacks]
    config_topics = [t for t in registered_topics if t.endswith("/config")]
    command_topics = [t for t in registered_topics if t.endswith("/set")]
    assert len(config_topics) > 0
    assert len(command_topics) > 0


# ---------------------------------------------------------------------------
# ha_ready 게이트 메커니즘
# ---------------------------------------------------------------------------


def test_ha_ready_set_after_retained_config_message(mock_config, mqtt_client):
    """on_connect 이후 retained config 메시지를 수신하면 ha_ready가 설정되는지 검증."""
    panel = Panel(mock_config, mqtt_client, MagicMock())
    panel._loop = _make_sync_loop()

    _fire_connect(mqtt_client)
    assert not panel.ha_ready.is_set()  # 아직 준비 안 됨
    assert panel.ha_registry is not False

    # broker가 retained 메시지를 돌려주는 상황 시뮬레이션
    _dispatch(mqtt_client, panel.ha_registry, "{}")

    assert panel.ha_ready.is_set()


def test_ha_ready_not_set_if_wrong_topic_arrives(mock_config, mqtt_client):
    """ha_registry와 다른 토픽이 오면 ha_ready가 설정되지 않아야 한다."""
    panel = Panel(mock_config, mqtt_client, MagicMock())
    panel._loop = _make_sync_loop()

    _fire_connect(mqtt_client)

    wrong_topic = "homeassistant/light/livingroom_light0/config"  # ha_registry가 아닌 토픽
    _dispatch(mqtt_client, wrong_topic, "{}")

    # ha_registry(마지막 config 토픽)가 아닌 메시지로는 해제 안 됨
    if panel.ha_registry != wrong_topic:
        assert not panel.ha_ready.is_set()


# ---------------------------------------------------------------------------
# Race condition regression
# ---------------------------------------------------------------------------


def test_connect_before_panel_init_prevents_on_connect(mock_config, mqtt_client):
    """Regression: connect()를 패널 초기화 이전에 호출하면 on_connect가 발화하지 않는다."""
    # BUG 재현: 연결을 패널 생성 이전에 발화 (콜백/토픽 미등록 상태)
    _fire_connect(mqtt_client)

    panel = Panel(mock_config, mqtt_client, MagicMock())

    # on_connect가 발화하지 않았으므로 discovery 미발행 → ha_registry 미설정
    assert panel.ha_registry is False
    # ha_ready 미설정 — HA 명령이 모두 무시됨
    assert not panel.ha_ready.is_set()


def test_connect_after_panel_init_enables_scan(mock_config, mqtt_client):
    """Fix 검증: connect()를 패널 초기화 이후에 호출하면 on_connect가 정상 발화한다."""
    panel = Panel(mock_config, mqtt_client, MagicMock())  # 콜백/토픽 등록 완료
    panel._loop = _make_sync_loop()

    _fire_connect(mqtt_client)  # 이제 자동 구독 + discovery 발행

    assert panel.ha_registry is not False

    # retained 메시지 도착 → ha_ready 설정
    _dispatch(mqtt_client, panel.ha_registry, "{}")

    assert panel.ha_ready.is_set()

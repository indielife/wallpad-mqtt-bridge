from unittest.mock import MagicMock

from wallpad.ha.discovery import HaDiscoveryCoordinator, HandshakeHaDiscoveryCoordinator
from wallpad.mqtt import TOPIC_BRIDGE_REMOVE, TOPIC_BRIDGE_RESTART


def _make_device(payloads: list[tuple[str, str]]):
    device = MagicMock()
    device.get_discovery_payloads.return_value = payloads
    return device


# ---------------------------------------------------------------------------
# HaDiscoveryCoordinator (base)
# ---------------------------------------------------------------------------


def test_publish_sends_each_device_payload_retained():
    mqtt_client = MagicMock()
    device_a = _make_device([("topic/a/config", '{"a": 1}')])
    device_b = _make_device([("topic/b/config", '{"b": 1}')])
    coordinator = HaDiscoveryCoordinator(mqtt_client, [device_a, device_b])

    coordinator.publish()

    mqtt_client.publish.assert_any_call("topic/a/config", '{"a": 1}', retain=True)
    mqtt_client.publish.assert_any_call("topic/b/config", '{"b": 1}', retain=True)


def test_publish_remove_forwards_flag_to_devices():
    mqtt_client = MagicMock()
    device = _make_device([("topic/a/config", "")])
    coordinator = HaDiscoveryCoordinator(mqtt_client, [device])

    coordinator.publish(remove=True)

    device.get_discovery_payloads.assert_called_once_with(remove=True)


def test_register_routes_wires_restart_and_remove():
    mqtt_client = MagicMock()
    coordinator = HaDiscoveryCoordinator(mqtt_client, [])

    coordinator.register_routes()

    registered = {c.args[0]: c.args[1] for c in mqtt_client.register_topic_callback.call_args_list}
    assert registered[TOPIC_BRIDGE_RESTART] == coordinator._handle_restart
    assert registered[TOPIC_BRIDGE_REMOVE] == coordinator._handle_remove


def test_handle_restart_republishes_without_remove_flag():
    mqtt_client = MagicMock()
    coordinator = HaDiscoveryCoordinator(mqtt_client, [])
    coordinator.publish = MagicMock()

    coordinator._handle_restart("wallpad/bridge/config/restart", "")

    coordinator.publish.assert_called_once_with()


def test_handle_remove_republishes_with_remove_flag():
    mqtt_client = MagicMock()
    coordinator = HaDiscoveryCoordinator(mqtt_client, [])
    coordinator.publish = MagicMock()

    coordinator._handle_remove("wallpad/bridge/config/remove", "")

    coordinator.publish.assert_called_once_with(remove=True)


def test_on_connect_publishes_discovery():
    mqtt_client = MagicMock()
    coordinator = HaDiscoveryCoordinator(mqtt_client, [])
    coordinator.publish = MagicMock()

    coordinator.on_connect(MagicMock(), None, {}, 0)

    coordinator.publish.assert_called_once_with()


# ---------------------------------------------------------------------------
# HandshakeHaDiscoveryCoordinator
# ---------------------------------------------------------------------------


def _make_handshake_coordinator(devices, loop=None):
    mqtt_client = MagicMock()
    coordinator = HandshakeHaDiscoveryCoordinator(mqtt_client, devices, loop_provider=lambda: loop)
    return coordinator, mqtt_client


def test_publish_sets_expected_echo_topic_to_last_published_topic():
    device_a = _make_device([("topic/a/config", "{}")])
    device_b = _make_device([("topic/b1/config", "{}"), ("topic/b2/config", "{}")])
    coordinator, _ = _make_handshake_coordinator([device_a, device_b])

    coordinator.publish()

    assert coordinator.expected_echo_topic == "topic/b2/config"


def test_publish_clears_ha_ready_and_expected_echo_topic_before_publishing():
    coordinator, _ = _make_handshake_coordinator([])
    coordinator.ha_ready.set()
    coordinator.expected_echo_topic = "stale/topic"

    coordinator.publish()

    assert not coordinator.ha_ready.is_set()
    assert coordinator.expected_echo_topic is None


def test_expected_echo_topic_is_set_before_any_publish_call():
    """에코백이 발행 도중에 도착해도 매칭을 놓치지 않도록, 첫 publish 호출
    시점에 이미 expected_echo_topic이 최종 토픽으로 확정돼 있어야 한다."""
    device_a = _make_device([("topic/a/config", "{}")])
    device_b = _make_device([("topic/b/config", "{}")])
    coordinator, mqtt_client = _make_handshake_coordinator([device_a, device_b])

    seen: list[str | None] = []
    mqtt_client.publish.side_effect = lambda *a, **k: seen.append(coordinator.expected_echo_topic)

    coordinator.publish()

    # 모든 발행 시점에 이미 마지막 토픽으로 확정돼 있어야 한다
    assert seen == ["topic/b/config", "topic/b/config"]


def test_handle_echo_sets_ha_ready_when_topic_matches():
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = lambda f: f()
    device = _make_device([("topic/a/config", "{}")])
    coordinator, _ = _make_handshake_coordinator([device], loop=loop)
    coordinator.publish()

    coordinator.handle_echo("topic/a/config", "{}")

    assert coordinator.ha_ready.is_set()


def test_handle_echo_does_not_set_ha_ready_when_topic_differs():
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = lambda f: f()
    device = _make_device([("topic/a/config", "{}")])
    coordinator, _ = _make_handshake_coordinator([device], loop=loop)
    coordinator.publish()

    coordinator.handle_echo("topic/other/config", "{}")

    assert not coordinator.ha_ready.is_set()


def test_handle_echo_before_first_publish_is_noop():
    """publish() 호출 전(expected_echo_topic이 None)에는 어떤 echo도 매칭되지 않는다."""
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = lambda f: f()
    coordinator, _ = _make_handshake_coordinator([], loop=loop)

    coordinator.handle_echo("topic/a/config", "{}")

    assert not coordinator.ha_ready.is_set()


def test_handle_echo_without_loop_does_not_raise():
    """루프가 아직 없어도(핸드셰이크 이전 시점) 예외 없이 무시된다."""
    device = _make_device([("topic/a/config", "{}")])
    coordinator, _ = _make_handshake_coordinator([device], loop=None)
    coordinator.publish()

    coordinator.handle_echo("topic/a/config", "{}")

    assert not coordinator.ha_ready.is_set()

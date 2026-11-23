"""HA에서 난방 명령 확인 결과를 읽을 수 있는 MQTT 계약."""

import json
import time


def test_diagnostic_discovery_is_enabled_and_removed_with_thermostat(e2e_panel):
    panel, mqtt, _ = e2e_panel
    panel.ha_coordinator.publish()
    topic = "homeassistant/sensor/livingroom_heating_command/config"
    messages = {t: p for t, p, _ in mqtt.published}
    payload = json.loads(messages[topic])
    climate = json.loads(messages["homeassistant/climate/livingroom/config"])
    assert payload["entity_category"] == "diagnostic"
    assert payload["enabled_by_default"] is True
    assert payload["device"] == climate["device"]
    assert payload["unique_id"] != climate["unique_id"]
    assert payload["state_topic"] == "wallpad/diagnostic/heating/livingroom"
    assert "명령 미확인" in payload["options"]
    assert "명령 미확인" in payload["value_template"]
    assert topic == panel.ha_coordinator.expected_echo_topic
    assert any(pattern == topic for pattern, _, _ in mqtt.topic_callbacks)
    panel.ha_coordinator.publish(remove=True)
    assert (topic, "", True) in mqtt.published


async def test_diagnostic_follows_pending_sent_and_confirmed(e2e_panel):
    panel, mqtt, _ = e2e_panel
    topic = "wallpad/diagnostic/heating/livingroom"
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    assert mqtt.json_for(topic)[-1]["status"] == "pending"
    assert mqtt.json_for("homeassistant/climate/livingroom/state")[-1]["target_temp"] == 22
    now = time.monotonic()
    panel.device_states["thermostat"]["livingroom"].scan.tick = now
    await panel.synchronizer.sync_once(now)
    assert mqtt.json_for(topic)[-1]["attempts"] == 1
    panel.process_packet("aa5530d00036000100001100160014000000720d0d")
    diagnostic = mqtt.json_for(topic)[-1]
    assert diagnostic["status"] == "confirmed"
    assert diagnostic["last_received"]["mode"] == "heat"
    assert diagnostic["last_received_at"]
    assert diagnostic["requested_at"]
    assert diagnostic["last_sent_at"]
    assert all(retain for t, _, retain in mqtt.published_json if t == topic)


def test_reconnect_republishes_current_status_and_new_instance_starts_idle(e2e_panel):
    panel, mqtt, _ = e2e_panel
    topic = "wallpad/diagnostic/heating/livingroom"
    for callback in mqtt.connect_callbacks:
        callback()
    assert mqtt.json_for(topic)[-1]["status"] == "idle"
    panel.ha_ready.set()
    mqtt.deliver("homeassistant/climate/livingroom/mode", "off")
    before = mqtt.json_for(topic)[-1]
    for callback in mqtt.connect_callbacks:
        callback()
    assert mqtt.json_for(topic)[-1] == before


def test_unconfirmed_diagnostic_has_reason_and_is_isolated_by_room(e2e_panel_multiroom):
    panel, mqtt, _ = e2e_panel_multiroom
    mqtt.deliver("homeassistant/climate/livingroom/mode", "off")
    panel.heating_commands["livingroom"].mark_unconfirmed("retry_exhausted")
    value = mqtt.json_for("wallpad/diagnostic/heating/livingroom")[-1]
    assert value["status"] == "unconfirmed"
    assert value["reason"] == "retry_exhausted"
    assert not mqtt.json_for("wallpad/diagnostic/heating/bedroom")


async def test_repeated_bus_deferral_does_not_flood_diagnostic_topic(e2e_panel):
    panel, mqtt, transport = e2e_panel
    topic = "wallpad/diagnostic/heating/livingroom"
    mqtt.deliver("homeassistant/climate/livingroom/mode", "off")
    transport.write_if_idle.return_value = False
    now = time.monotonic()
    panel.device_states["thermostat"]["livingroom"].scan.tick = now
    for _ in range(10):
        await panel.synchronizer.sync_once(now)
    assert len(mqtt.json_for(topic)) == 2
    assert mqtt.json_for(topic)[-1]["reason"] == "bus_busy"

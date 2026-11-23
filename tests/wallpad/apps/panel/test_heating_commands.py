"""난방 요청의 실제 송신·수신·시간 초과를 경계에서 검증한다."""

import time

import pytest

from wallpad.apps.panel.send_result import SendResult


async def _sync(panel):
    now = time.monotonic()
    for device in panel.device_states.values():
        for room in device.values():
            room.scan.tick = now
    await panel.synchronizer.sync_once(now)


async def test_one_heating_request_writes_one_combined_frame(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    await _sync(panel)
    assert transport.write_if_idle.await_count == 1


async def test_missing_response_becomes_unconfirmed_after_five_writes(e2e_panel, monkeypatch):
    panel, mqtt, transport = e2e_panel
    clock = [500.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    for _ in range(6):
        await _sync(panel)
        clock[0] += 2.0
    command = panel.heating_commands["livingroom"]
    assert command.status == "unconfirmed"
    assert command.reason == "retry_exhausted"
    assert transport.write_if_idle.await_count == 5
    assert command.attempts == 5


async def test_late_matching_response_confirms_only_current_request(e2e_panel, monkeypatch):
    panel, mqtt, _ = e2e_panel
    clock = [500.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    await _sync(panel)
    command = panel.heating_commands["livingroom"]
    command.observe({"mode": "heat", "target_temp": 22, "current_temp": 20})
    assert command.status == "pending"
    command.mark_unconfirmed("retry_exhausted")
    command.observe({"mode": "heat", "target_temp": 25, "current_temp": 20})
    assert command.status == "confirmed"
    assert command.confirmed_late is True
    mqtt.deliver("homeassistant/climate/livingroom/mode", "off")
    assert command.status == "pending"
    assert command.attempts == 0
    assert command.confirmed_late is False
    command.observe({"mode": "heat", "target_temp": 25, "current_temp": 20})
    assert command.status == "pending"


@pytest.mark.parametrize("result", [SendResult.INVALID, SendResult.FAILED])
async def test_unsendable_request_is_visible_without_retries(e2e_panel, result):
    from unittest.mock import AsyncMock

    panel, mqtt, _ = e2e_panel
    panel.synchronizer.send_packet = AsyncMock(return_value=result)
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    await _sync(panel)
    command = panel.heating_commands["livingroom"]
    assert command.status == "unconfirmed"
    assert command.reason == result.value
    assert command.attempts == 0


async def test_new_request_during_write_cannot_inherit_old_result(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")

    async def replace_request(data):
        mqtt.deliver("homeassistant/climate/livingroom/target_temp", "26")
        return True

    transport.write_if_idle.side_effect = replace_request
    await _sync(panel)
    command = panel.heating_commands["livingroom"]
    assert command.requested["target_temp"] == 26
    assert command.attempts == 0
    assert command.waiting_since is None
    assert command.status == "pending"


async def test_busy_bus_does_not_count_attempts_or_block_timeout(e2e_panel, monkeypatch):
    panel, mqtt, transport = e2e_panel
    clock = [500.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    transport.write_if_idle.return_value = False
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    await _sync(panel)
    command = panel.heating_commands["livingroom"]
    assert command.status == "pending"
    assert command.attempts == 0
    assert command.waiting_since is None
    transport.write_if_idle.return_value = True
    await _sync(panel)
    assert command.attempts == 1
    transport.is_idle.return_value = False
    clock[0] += 2.0
    await _sync(panel)
    assert command.waiting_since is None
    assert command.attempts == 1


async def test_ha_debug_packet_cannot_confirm_a_command(e2e_panel):
    panel, mqtt, _ = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    await _sync(panel)
    packet = "aa5530d00036000100001100160014000000720d0d"
    panel.process_packet(packet, source="HA")
    assert panel.heating_commands["livingroom"].status == "pending"
    panel.process_packet(packet)
    assert panel.heating_commands["livingroom"].status == "confirmed"


async def test_matching_state_before_any_write_does_not_confirm(e2e_panel):
    panel, mqtt, _ = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    command = panel.heating_commands["livingroom"]
    command.observe({"mode": "heat", "target_temp": 22, "current_temp": 20})
    assert command.status == "pending"


async def test_response_during_write_is_not_lost(e2e_panel):
    panel, mqtt, transport = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")

    async def reply(data):
        panel.process_packet("aa5530d00036000100001100160014000000720d0d")
        return True

    transport.write_if_idle.side_effect = reply
    await _sync(panel)
    command = panel.heating_commands["livingroom"]
    assert command.status == "confirmed"
    assert command.attempts == 1


async def test_heating_command_callback_runs_on_owner_loop(e2e_panel):
    import asyncio

    panel, mqtt, _ = e2e_panel
    panel._loop = asyncio.get_running_loop()
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "25")
    await asyncio.sleep(0)
    assert panel.heating_commands["livingroom"].requested["target_temp"] == 25


async def test_preexisting_matching_sample_is_not_reused_after_write(e2e_panel):
    panel, mqtt, _ = e2e_panel
    packet = "aa5530d00036000100001100160014000000720d0d"
    panel.process_packet(packet)
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    await _sync(panel)
    assert panel.heating_commands["livingroom"].status == "pending"


async def test_off_confirmation_uses_received_mode_and_keeps_optimistic_contract(e2e_panel):
    panel, mqtt, _ = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/mode", "off")
    assert mqtt.json_for("homeassistant/climate/livingroom/state")[-1]["mode"] == "off"
    await _sync(panel)
    command = panel.heating_commands["livingroom"]
    command.observe({"mode": "off", "target_temp": 22, "current_temp": 20})
    assert command.status == "confirmed"
    assert command.requested == {"mode": "off"}


async def test_other_room_response_cannot_confirm_request(e2e_panel_multiroom):
    panel, mqtt, _ = e2e_panel_multiroom
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    await _sync(panel)
    packet = "aa5530d00036010100001100160014000000730d0d"
    panel.process_packet(packet)
    assert panel.heating_commands["livingroom"].status == "pending"
    assert panel.heating_commands["bedroom"].status == "idle"


async def test_damaged_tail_cannot_confirm_heating_command(e2e_panel):
    panel, mqtt, _ = e2e_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    await _sync(panel)
    packet = "aa5530d00036000100001100160014000000720d00"
    panel.process_packet(packet)
    assert panel.heating_commands["livingroom"].status == "pending"

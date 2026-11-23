"""단조 시계의 원점과 무관하게 기동·수동 스캔을 즉시 시작한다."""

import time

import pytest

_THERMOSTAT_QUERY = bytes.fromhex("aa5530bc00360001003a00000000000000005d0d0d")


@pytest.mark.parametrize("now", [0.0, 0.5, 50.0])
async def test_startup_queries_immediately_after_host_boot(e2e_panel, monkeypatch, now):
    panel, _mqtt, transport = e2e_panel
    panel.config.packet_delay = 0
    monkeypatch.setattr(time, "monotonic", lambda: now)
    await panel.synchronizer.sync_once(now)
    assert _THERMOSTAT_QUERY in [c.args[0] for c in transport.write_if_idle.await_args_list]


@pytest.mark.parametrize("now", [0.0, 0.5, 50.0])
async def test_manual_scan_topic_queries_immediately_after_host_boot(e2e_panel, monkeypatch, now):
    panel, mqtt, transport = e2e_panel
    panel.config.packet_delay = 0
    monkeypatch.setattr(time, "monotonic", lambda: now)
    for device in panel.device_states.values():
        for room in device.values():
            room.scan.tick = now
            room.scan.last = now
    await panel.synchronizer.sync_once(now)
    transport.write_if_idle.assert_not_awaited()
    mqtt.deliver("wallpad/bridge/config/scan", "")
    await panel.synchronizer.sync_once(now)
    assert _THERMOSTAT_QUERY in [c.args[0] for c in transport.write_if_idle.await_args_list]

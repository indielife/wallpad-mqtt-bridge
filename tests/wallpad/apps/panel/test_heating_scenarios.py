"""운영 조사 절차와 같은 순서로 송수신·HA·소진 로그를 비교한다."""

import asyncio
import time

import pytest


async def _receive(panel, transport, packet):
    transport.read.side_effect = [
        *[bytes.fromhex(packet[i : i + 2]) for i in range(0, len(packet), 2)],
        asyncio.CancelledError(),
    ]
    with pytest.raises(asyncio.CancelledError):
        await panel.receive_packets()


async def _sync(panel, now):
    for device in panel.device_states.values():
        for room in device.values():
            room.scan.tick = now
    await panel.synchronizer.sync_once(now)


async def test_missing_heating_confirmation_can_be_investigated_end_to_end(
    e2e_panel, monkeypatch, caplog
):
    panel, mqtt, transport = e2e_panel
    clock = [500.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    caplog.set_level("DEBUG")
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    await _sync(panel, clock[0])
    # 조명은 정상 통신하지만 난방은 요청과 다른 off를 응답한다.
    await _receive(panel, transport, "aa5530d0000e00010000ff000000000000000e0d0d")
    await _receive(panel, transport, "aa5530d00036000100000100160014000000620d0d")
    # 이후 난방 응답은 체크섬이 손상되어 확인에 사용할 수 없다.
    await _receive(panel, transport, "aa5530d00036000100001100160014000000ff0d0d")
    for _ in range(5):
        clock[0] += 2.0
        await _sync(panel, clock[0])
    diagnostic = mqtt.json_for("wallpad/diagnostic/heating/livingroom")[-1]
    assert diagnostic["status"] == "unconfirmed"
    assert diagnostic["attempts"] == 5
    assert diagnostic["last_received"]["mode"] == "off"
    assert mqtt.json_for("homeassistant/light/livingroom/state")
    warning = next(r.message for r in caplog.records if "event=heating_unconfirmed" in r.message)
    assert "last_received=" in warning
    assert "last_received_at=" in warning
    assert "reason=checksum" in caplog.text
    await _receive(panel, transport, "aa5530d00036000100001100160014000000720d0d")
    assert mqtt.json_for("wallpad/diagnostic/heating/livingroom")[-1]["confirmed_late"] is True

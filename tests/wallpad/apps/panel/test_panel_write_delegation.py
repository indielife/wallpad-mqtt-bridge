"""Panel의 send_packet/_schedule_write가 버스 중재를 transport.write_if_idle에
위임하는지 검증합니다. 정숙 간격 판정 자체는 BusArbitrationTransport 레벨에서
tests/wallpad/transport/test_bus_arbitration.py가 검증합니다."""

import asyncio
from unittest.mock import AsyncMock


async def test_schedule_write_delegates_to_write_if_idle(panel_instance, monkeypatch):
    panel_instance.transport = AsyncMock()
    panel_instance._loop = asyncio.get_running_loop()

    captured = {}
    monkeypatch.setattr(
        "wallpad.apps.panel.panel.asyncio.run_coroutine_threadsafe",
        lambda coro, loop: captured.setdefault("task", asyncio.ensure_future(coro)),
    )

    panel_instance._schedule_write("aa5530bc")
    await captured["task"]

    panel_instance.transport.write_if_idle.assert_awaited_once_with(bytearray.fromhex("aa5530bc"))


async def test_send_packet_delegates_to_write_if_idle(panel_instance, monkeypatch):
    panel_instance.transport = AsyncMock()
    panel_instance.transport.write_if_idle.return_value = True
    monkeypatch.setattr(panel_instance, "make_packet", lambda *a, **k: "aa5530bc")
    monkeypatch.setattr(
        panel_instance.parser,
        "parse_frame",
        lambda *a, **k: {
            "type": "send",
            "command": "상태",
            "src_device": "wallpad",
            "src_room": "livingroom",
            "dst_device": "light",
            "dst_room": "livingroom",
            "value": "on",
        },
    )

    await panel_instance.send_packet("light", "livingroom", "1", "on")

    panel_instance.transport.write_if_idle.assert_awaited_once_with(bytearray.fromhex("aa5530bc"))


async def test_send_packet_returns_early_when_bus_busy(panel_instance, monkeypatch):
    panel_instance.transport = AsyncMock()
    panel_instance.transport.write_if_idle.return_value = False
    monkeypatch.setattr(panel_instance, "make_packet", lambda *a, **k: "aa5530bc")

    await panel_instance.send_packet("light", "livingroom", "1", "on")

    panel_instance.transport.write_if_idle.assert_awaited_once_with(bytearray.fromhex("aa5530bc"))

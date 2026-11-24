"""실제 버스 중재·재연결·소켓 쓰기 경계에서 명령 확인을 검증한다."""

import asyncio
import contextlib
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from wallpad.transport.bus_arbitration import BusArbitrationTransport
from wallpad.transport.reconnect import ReconnectingTransport
from wallpad.transport.socket import SocketTransport

_ACK = bytes.fromhex("aa5530d00036000100001100160014000000720d0d")


@pytest.fixture
async def socket_panel(e2e_panel):
    panel, mqtt, _ = e2e_panel
    reader = asyncio.StreamReader()
    writer = MagicMock(drain=AsyncMock())
    socket = SocketTransport("test", 8899)
    socket._reader = reader
    socket._writer = writer
    transport = BusArbitrationTransport(
        ReconnectingTransport(socket, reconnect_interval=0), idle_interval=0
    )
    transport._last_activity = 0.0
    panel.transport = transport
    panel.synchronizer.is_bus_idle = transport.is_idle
    return panel, mqtt, socket, reader, writer


async def _sync(panel):
    now = time.monotonic()
    for device in panel.device_states.values():
        for room in device.values():
            room.scan.tick = now
    await panel.synchronizer.sync_once(now)


@pytest.mark.parametrize("failure", ["write", "drain"])
async def test_reconnect_wait_observation_does_not_confirm_later_write(socket_panel, failure):
    panel, mqtt, socket, reader, writer = socket_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    command = panel.heating_commands["livingroom"]
    observed = asyncio.Event()
    original_callback = command.on_change

    def record(snapshot):
        original_callback(snapshot)
        if snapshot["last_received"] is not None:
            observed.set()

    command.on_change = record

    async def reconnect():
        reader.feed_data(_ACK)
        await asyncio.wait_for(observed.wait(), timeout=1)

    socket.connect = AsyncMock(side_effect=reconnect)
    if failure == "write":
        writer.write.side_effect = [OSError("write failed"), None]
    else:
        writer.drain.side_effect = [OSError("drain failed"), None]

    receive_task = asyncio.create_task(panel.receive_packets())
    try:
        await asyncio.wait_for(_sync(panel), timeout=3)
        assert writer.write.call_count == 2
        assert command.attempts == 1
        assert command.status == "pending"
        observed.clear()
        reader.feed_data(_ACK)
        await asyncio.wait_for(observed.wait(), timeout=1)
        assert command.status == "confirmed"
    finally:
        receive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await receive_task


async def test_reply_during_actual_socket_drain_is_preserved(socket_panel):
    panel, mqtt, _socket, reader, writer = socket_panel
    mqtt.deliver("homeassistant/climate/livingroom/target_temp", "22")
    command = panel.heating_commands["livingroom"]
    observed = asyncio.Event()
    original_callback = command.on_change

    def record(snapshot):
        original_callback(snapshot)
        if snapshot["last_received"] is not None:
            observed.set()

    command.on_change = record

    async def drain():
        reader.feed_data(_ACK)
        await asyncio.wait_for(observed.wait(), timeout=1)

    writer.drain.side_effect = drain
    receive_task = asyncio.create_task(panel.receive_packets())
    try:
        await asyncio.wait_for(_sync(panel), timeout=3)
        assert command.status == "confirmed"
        assert command.attempts == 1
    finally:
        receive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await receive_task

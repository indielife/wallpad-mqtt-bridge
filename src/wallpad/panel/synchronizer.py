import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from wallpad.config import AppConfig
from wallpad.panel.state import KocomStateManager, RoomState, ScanState, SubDeviceState
from wallpad.protocol.kocom.constants import DEVICE_ELEVATOR, DEVICE_GAS

logger = logging.getLogger(__name__)

POLL_STEP_INTERVAL = 2
POLL_BURST_LIMIT = 4
RECONCILE_RETRY_LIMIT = 4
RECONCILE_RETRY_INTERVAL = 1
GAS_CONFIRM_EXTRA_DELAY = 5

SendPacket = Callable[..., Awaitable[None]]
IsBusIdle = Callable[[], bool]


class StateSynchronizer:
    """HA가 원하는 상태(set)와 RS485 실제 상태(state)를 맞추는 워커.

    성격이 다른 두 루프를 함께 돈다:
    - poll: `scan_interval`마다 방 전체에 `조회`를 broadcast해 상태를 확인한다.
    - reconcile: HA 명령으로 걸린 `set`을 디바이스가 확인해줄 때까지 재전송한다.

    둘 다 주입받은 send_packet 하나만 거쳐 버스에 쓰므로, 실제 버스 쓰기의
    유일성(단일 쓰기 경로) 보장은 이 클래스가 아니라 send_packet이 내부적으로
    위임하는 BusArbitrationTransport.write_if_idle의 책임이다.
    """

    def __init__(
        self,
        device_states: KocomStateManager,
        send_packet: SendPacket,
        config: AppConfig,
        is_bus_idle: IsBusIdle,
        ha_ready: asyncio.Event,
    ) -> None:
        self.device_states = device_states
        self.send_packet = send_packet
        self.config = config
        self.is_bus_idle = is_bus_idle
        self.ha_ready = ha_ready

    async def run(self) -> None:
        await self.ha_ready.wait()
        while True:
            now = time.time()
            if self.is_bus_idle():
                try:
                    await self.sync_once(now)
                except Exception as e:
                    logger.debug("Sync failed: %r", e)
            await asyncio.sleep(0.2)

    async def sync_once(self, now: float) -> None:
        for device, device_state in self.device_states.items():
            for room, room_state in device_state.items():
                await self.sync_room(device, room, room_state, now)

    async def sync_room(self, device: str, room: str, room_state: RoomState, now: float) -> None:
        if device == DEVICE_ELEVATOR:
            for sub_device, sub_state in room_state.sub_devices.items():
                await self.reconcile_device(device, room, sub_device, sub_state, now)
            return

        scan_state = room_state.scan
        if now - scan_state.tick > self.config.scan_interval:
            await self.poll_room(device, room, scan_state, now)
        else:
            for sub_device, sub_state in room_state.sub_devices.items():
                await self.reconcile_device(device, room, sub_device, sub_state, now)

    async def poll_room(self, device: str, room: str, scan_state: ScanState, now: float) -> None:
        if now - scan_state.last > POLL_STEP_INTERVAL:
            scan_state.count += 1
            scan_state.last = now
            await self.send_packet(device, room, "", "", cmd="조회")
            await asyncio.sleep(self.config.packet_delay)
        if scan_state.count > POLL_BURST_LIMIT:
            scan_state.tick = now
            scan_state.count = 0
            scan_state.last = 0

    async def reconcile_device(
        self, device: str, room: str, sub_device: str, sub_state: SubDeviceState, now: float
    ) -> None:
        if sub_state.count > RECONCILE_RETRY_LIMIT:
            sub_state.count = 0
            sub_state.last = "state"
        elif sub_state.last == "set":
            sub_state.last = now
            if device == DEVICE_GAS:
                sub_state.last += GAS_CONFIRM_EXTRA_DELAY
            elif device == DEVICE_ELEVATOR:
                sub_state.last = "state"
            await self.send_packet(device, room, sub_device, sub_state.set)
        elif isinstance(sub_state.last, float) and now - sub_state.last > RECONCILE_RETRY_INTERVAL:
            sub_state.last = "set"
            sub_state.count += 1

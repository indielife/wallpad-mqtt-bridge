import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from wallpad.apps.panel.heating_commands import HeatingCommandTracker
from wallpad.apps.panel.send_result import SendResult
from wallpad.apps.panel.state import KocomStateManager, RoomState, ScanState, SubDeviceState
from wallpad.config import AppConfig
from wallpad.protocol.kocom.constants import DEVICE_ELEVATOR, DEVICE_GAS, DEVICE_THERMOSTAT

logger = logging.getLogger(__name__)

POLL_STEP_INTERVAL = 2
POLL_BURST_LIMIT = 4
RECONCILE_RETRY_LIMIT = 4
RECONCILE_RETRY_INTERVAL = 1
GAS_CONFIRM_EXTRA_DELAY = 5

SendPacket = Callable[..., Awaitable[SendResult]]
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
        heating_commands: dict[str, HeatingCommandTracker] | None = None,
    ) -> None:
        self.device_states = device_states
        self.send_packet = send_packet
        self.config = config
        self.is_bus_idle = is_bus_idle
        self.ha_ready = ha_ready
        self.heating_commands = heating_commands if heating_commands is not None else {}

    async def run(self) -> None:
        await self.ha_ready.wait()
        while True:
            now = time.monotonic()
            try:
                await self.sync_once(now)
            except Exception:
                logger.exception("event=sync_failed")
            await asyncio.sleep(0.2)

    async def sync_once(self, now: float) -> None:
        for device, device_state in self.device_states.items():
            for room, room_state in device_state.items():
                await self.sync_room(device, room, room_state, now)

    async def sync_room(self, device: str, room: str, room_state: RoomState, now: float) -> None:
        if device == DEVICE_THERMOSTAT and room in self.heating_commands:
            await self._sync_heating(room, room_state, now)
            return
        if device == DEVICE_ELEVATOR:
            for sub_device, sub_state in room_state.sub_devices.items():
                await self.reconcile_device(device, room, sub_device, sub_state, now)
            return

        # 이미 전송한 요청의 시간 초과는 버스 혼잡·스캔 우선순위와 무관하게 처리한다.
        waiting = {
            sub_device
            for sub_device, sub_state in room_state.sub_devices.items()
            if isinstance(sub_state.last, float)
        }
        for sub_device in waiting:
            await self.reconcile_device(device, room, sub_device, room_state[sub_device], now)

        scan_state = room_state.scan
        if now - scan_state.tick > self.config.scan_interval:
            await self.poll_room(device, room, scan_state, now)
        else:
            for sub_device, sub_state in room_state.sub_devices.items():
                if sub_device not in waiting:
                    await self.reconcile_device(device, room, sub_device, sub_state, now)

    async def _sync_heating(self, room: str, room_state: RoomState, now: float) -> None:
        command = self.heating_commands[room]
        if (
            command.status == "pending"
            and command.waiting_since is not None
            and now - command.waiting_since > RECONCILE_RETRY_INTERVAL
        ):
            command.timeout(exhausted=command.attempts > RECONCILE_RETRY_LIMIT)

        if now - room_state.scan.tick > self.config.scan_interval:
            await self.poll_room(DEVICE_THERMOSTAT, room, room_state.scan, now)
        elif command.status == "pending" and command.waiting_since is None and self.is_bus_idle():
            request_id = command.start_send()
            result = await self.send_packet(DEVICE_THERMOSTAT, room, "", "", request_id=request_id)
            command.finish_send(request_id, result)

        if command.status in ("confirmed", "unconfirmed"):
            for sub_state in room_state.sub_devices.values():
                sub_state.last = "state"
                sub_state.count = 0

    async def poll_room(self, device: str, room: str, scan_state: ScanState, now: float) -> None:
        if self.is_bus_idle() and now - scan_state.last > POLL_STEP_INTERVAL:
            result = await self.send_packet(device, room, "", "", cmd="조회")
            if result is SendResult.SENT:
                scan_state.count += 1
                scan_state.last = time.monotonic()
                await asyncio.sleep(self.config.packet_delay)
        if scan_state.count > POLL_BURST_LIMIT:
            scan_state.tick = now
            scan_state.count = 0
            scan_state.last = 0

    async def reconcile_device(
        self, device: str, room: str, sub_device: str, sub_state: SubDeviceState, now: float
    ) -> None:
        if sub_state.last == "set" and self.is_bus_idle():
            value = sub_state.set
            result = await self.send_packet(device, room, sub_device, value)
            # 성공·실패 어느 결과도 쓰기 대기 중 도착한 새 요청이나 응답을 지우면 안 된다.
            if sub_state.last != "set" or sub_state.set != value:
                return
            if result is SendResult.DEFERRED:
                return
            if result is not SendResult.SENT:
                logger.warning(
                    "event=command_unsent device=%s room=%s target=%s result=%s",
                    device,
                    room,
                    sub_device,
                    result.value,
                )
                sub_state.last = "state"
                sub_state.count = 0
                return
            sub_state.last = time.monotonic()
            if device == DEVICE_GAS:
                sub_state.last += GAS_CONFIRM_EXTRA_DELAY
            elif device == DEVICE_ELEVATOR:
                sub_state.last = "state"
        elif isinstance(sub_state.last, float) and now - sub_state.last > RECONCILE_RETRY_INTERVAL:
            sub_state.count += 1
            logger.info(
                "event=response_timeout device=%s room=%s target=%s attempts=%s",
                device,
                room,
                sub_device,
                sub_state.count,
            )
            if sub_state.count > RECONCILE_RETRY_LIMIT:
                logger.warning(
                    "event=retry_exhausted device=%s room=%s target=%s requested=%s attempts=%s",
                    device,
                    room,
                    sub_device,
                    sub_state.set,
                    sub_state.count,
                )
                sub_state.last = "state"
                sub_state.count = 0
            else:
                sub_state.last = "set"

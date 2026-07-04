import asyncio
import time

from .base import BaseTransport

DEFAULT_IDLE_INTERVAL_SECONDS = 0.1


class BusArbitrationTransport(BaseTransport):
    """RS485 반이중 버스에서 충돌을 피하기 위해 마지막 버스 활동 시각을 추적하는
    decorator transport.

    `BaseTransport` 인터페이스(connect/read/write/close)는 그대로 위임하되, 매
    성공한 `read()`/`write()` 시점에 활동 시각을 갱신한다 — 프레임을 해독했는지와
    무관하게, 버스에 바이트가 오간 사실 자체가 "바쁘다"는 근거이기 때문이다.

    `BaseTransport`에는 없는 `is_idle()`/`write_if_idle()` 두 메서드를 추가로
    제공한다(ISP: Ventilator 등 이 문제를 겪지 않는 클라이언트는 이 메서드를 볼
    필요가 없다). 언제 재시도할지 같은 정책은 이 클래스가 아니라 호출자(예:
    StateSynchronizer)의 몫이다 — 이 클래스는 오직 "지금 써도 되는가"라는
    메커니즘만 책임진다.
    """

    def __init__(
        self, transport: BaseTransport, idle_interval: float = DEFAULT_IDLE_INTERVAL_SECONDS
    ):
        self._transport = transport
        self._idle_interval = idle_interval
        self._last_activity = time.monotonic()
        self._write_lock = asyncio.Lock()

    async def connect(self):
        await self._transport.connect()

    async def read(self, size: int) -> bytes:
        data = await self._transport.read(size)
        self._last_activity = time.monotonic()
        return data

    async def write(self, data: bytes):
        await self._transport.write(data)
        self._last_activity = time.monotonic()

    async def close(self):
        await self._transport.close()

    def is_idle(self) -> bool:
        """버스가 마지막 활동 이후 정숙 간격만큼 조용했는지 확인."""
        return time.monotonic() - self._last_activity > self._idle_interval

    async def write_if_idle(self, data: bytes) -> bool:
        """버스가 정숙할 때만 데이터를 씀.

        정숙 판정부터 실제 전송, 활동 시각 갱신까지를 락으로 원자화해 서로 다른
        코루틴(스캔 루프, MQTT 스레드에서 run_coroutine_threadsafe로 예약된 디버그
        에코 등)이 겹쳐 쓰는 것을 막는다. 버스가 바쁘면 아무것도 쓰지 않고 False를
        반환하며, 재시도 여부는 정책을 가진 호출자의 몫이다.
        """
        async with self._write_lock:
            if not self.is_idle():
                return False
            await self.write(data)
            return True

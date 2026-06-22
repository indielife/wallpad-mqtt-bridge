import asyncio
import contextlib
import logging

from .base import BaseTransport

logger = logging.getLogger(__name__)

RECONNECT_INTERVAL = 5.0
MAX_RECONNECT_INTERVAL = 60.0


class ReconnectingTransport(BaseTransport):
    def __init__(self, transport: BaseTransport, reconnect_interval: float = RECONNECT_INTERVAL):
        self._transport = transport
        self._reconnect_interval = reconnect_interval

    async def connect(self):
        delay = self._reconnect_interval
        while True:
            try:
                await self._transport.connect()
                logger.info("Connected successfully.")
                return
            except Exception as e:
                logger.warning("Connect failed: %r. Retrying in %.0fs...", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RECONNECT_INTERVAL)

    async def _reconnect(self):
        while True:
            with contextlib.suppress(OSError, RuntimeError):
                await self._transport.close()
            logger.warning("Connection lost. Reconnecting in %.0fs...", self._reconnect_interval)
            await asyncio.sleep(self._reconnect_interval)
            try:
                await self._transport.connect()
                logger.info("Reconnected successfully.")
                return
            except Exception as e:
                logger.error("Reconnect failed: %r", e)

    async def read(self, size: int) -> bytes:
        while True:
            try:
                return await self._transport.read(size)
            except Exception as e:
                logger.warning("Read error: %r", e)
                await self._reconnect()

    async def write(self, data: bytes):
        while True:
            try:
                await self._transport.write(data)
                return
            except Exception as e:
                logger.warning("Write error: %r", e)
                await self._reconnect()

    async def close(self):
        await self._transport.close()

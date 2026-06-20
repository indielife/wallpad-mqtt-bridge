import asyncio
import logging
import socket
import time

from .base import BaseTransport, ConnectionAdapter

logger = logging.getLogger(__name__)

RECONNECT_INTERVAL = 5  # seconds


class SocketTransport(BaseTransport):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None

    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def read(self, size: int) -> bytes:
        return await self._reader.read(size)

    async def write(self, data: bytes):
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        self._writer.close()


class SocketAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for TCP socket communication.

    소켓 연결이 끊기면 read()/write() 내부에서 자동으로 재연결을 시도합니다.
    """

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._connection = self._connect()

    def _connect(self) -> socket.socket:
        soc = socket.socket()
        soc.settimeout(10)
        soc.connect((self._host, self._port))
        soc.settimeout(None)
        return soc

    def _reconnect(self) -> None:
        """소켓 연결이 끊긴 경우 재연결될 때까지 반복 시도합니다."""
        while True:
            logger.warning(
                "Socket disconnected (%s:%s). Reconnecting in %ds...",
                self._host,
                self._port,
                RECONNECT_INTERVAL,
            )
            time.sleep(RECONNECT_INTERVAL)
            try:
                self._connection = self._connect()
                logger.info("Reconnected to %s:%s", self._host, self._port)
                return
            except Exception as e:
                logger.error("Reconnect failed (%s:%s): %r", self._host, self._port, e)

    def read(self) -> bytes:
        while True:
            try:
                data = self._connection.recv(1)
                if not data:
                    logger.warning("Socket connection closed (empty read).")
                    self._reconnect()
                    continue
                return data
            except OSError:
                self._reconnect()

    def write(self, data: bytes) -> int:
        while True:
            try:
                return self._connection.send(data)
            except OSError:
                self._reconnect()

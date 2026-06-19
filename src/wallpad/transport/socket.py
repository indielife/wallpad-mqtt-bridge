import asyncio
import socket

from .base import BaseTransport, ConnectionAdapter


class SocketTransport(BaseTransport):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None

    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def read(self, size: int = 1) -> bytes:
        return await self._reader.read(size)

    async def write(self, data: bytes):
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        self._writer.close()


class SocketAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for TCP socket communication."""

    def __init__(self, host: str, port: int):
        try:
            soc = socket.socket()
            soc.settimeout(10)
            soc.connect((host, port))
            soc.settimeout(None)
            self._connection = soc
        except Exception as e:
            raise ConnectionError(f"Failed to connect to socket: {host}:{port}") from e

    def read(self) -> bytes:
        return self._connection.recv(1)

    def write(self, data: bytes) -> int:
        return self._connection.send(data)

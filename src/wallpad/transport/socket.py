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

    async def read(self, size: int) -> bytes:
        return await self._reader.read(size)

    async def write(self, data: bytes):
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        self._writer.close()


class SocketAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for TCP socket communication."""

    def __init__(self, connection: socket.socket):
        self._connection = connection

    def read(self) -> bytes:
        return self._connection.recv(1)

    def write(self, data: bytes) -> int:
        return self._connection.send(data)

    def is_open(self) -> bool:
        return self._connection is not None

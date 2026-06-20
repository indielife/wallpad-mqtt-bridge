import asyncio

from .base import BaseTransport


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

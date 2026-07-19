import asyncio

from .base import BaseTransport


class SocketTransport(BaseTransport):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def read(self, size: int) -> bytes:
        assert self._reader is not None, "connect()가 호출되지 않았습니다."
        return await self._reader.read(size)

    async def write(self, data: bytes):
        assert self._writer is not None, "connect()가 호출되지 않았습니다."
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        assert self._writer is not None, "connect()가 호출되지 않았습니다."
        self._writer.close()

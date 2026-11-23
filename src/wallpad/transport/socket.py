import asyncio

from .base import BaseTransport, WriteCallback


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
        data = await self._reader.read(size)
        if not data and size != 0:
            raise ConnectionError("소켓 EOF: 상대가 연결을 종료했습니다.")
        return data

    async def write(self, data: bytes, *, on_write: WriteCallback | None = None):
        assert self._writer is not None, "connect()가 호출되지 않았습니다."
        self._writer.write(data)
        if on_write is not None:
            on_write()
        await self._writer.drain()

    async def close(self):
        assert self._writer is not None, "connect()가 호출되지 않았습니다."
        self._writer.close()

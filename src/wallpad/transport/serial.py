import asyncio

import serial_asyncio_fast as serial_asyncio

from .base import BaseTransport


class SerialTransport(BaseTransport):
    def __init__(self, port: str, baud_rate: int):
        self.port = port
        self.baud_rate = baud_rate
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self):
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self.port, baudrate=self.baud_rate
        )

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

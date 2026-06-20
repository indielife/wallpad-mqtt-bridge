import serial_asyncio_fast as serial_asyncio

from .base import BaseTransport


class SerialTransport(BaseTransport):
    def __init__(self, port: str, baud_rate: int):
        self.port = port
        self.baud_rate = baud_rate
        self._reader = None
        self._writer = None

    async def connect(self):
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self.port, baudrate=self.baud_rate
        )

    async def read(self, size: int) -> bytes:
        return await self._reader.read(size)

    async def write(self, data: bytes):
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        self._writer.close()

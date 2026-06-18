import asyncio

import serial
import serial_asyncio

from .base import BaseTransport, ConnectionAdapter


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

    async def close(self):
        self._writer.close()


class SerialAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for serial communication."""

    def __init__(self, connection: serial.Serial):
        self._connection = connection

    def read(self) -> bytes:
        if not self._connection.readable():
            return ""
        return self._connection.read()

    def write(self, data: bytes) -> int:
        return self._connection.write(data)

    def is_open(self) -> bool:
        return (
            self._connection.is_open
            if hasattr(self._connection, "is_open")
            else self._connection.isOpen()
        )

import asyncio

import serial
import serial_asyncio_fast as serial_asyncio

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

    async def read(self, size: int = 1) -> bytes:
        return await self._reader.read(size)

    async def write(self, data: bytes):
        self._writer.write(data)

    async def close(self):
        self._writer.close()


class SerialAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for serial communication."""

    def __init__(self, port: str, baud_rate: int):
        try:
            ser = serial.Serial(port, baud_rate, timeout=None)
            ser.bytesize = 8
            ser.stopbits = 1
            ser.autoOpen = False
            self._connection = ser
        except Exception as e:
            raise ConnectionError(f"Failed to connect to serial port: {port}") from e

    def read(self) -> bytes:
        if not self._connection.readable():
            return b""
        return self._connection.read()

    def write(self, data: bytes) -> int:
        return self._connection.write(data)

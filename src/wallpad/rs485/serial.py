import serial

from wallpad.rs485.base import ConnectionAdapter


class SerialAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for serial communication."""

    def __init__(self, connection: serial.Serial):
        self._connection = connection

    def read(self) -> bytes:
        return self._connection.read()

    def write(self, data: bytes) -> int:
        return self._connection.write(data)

    def readable(self) -> bool:
        return self._connection.readable()

    def is_open(self) -> bool:
        return (
            self._connection.is_open
            if hasattr(self._connection, "is_open")
            else self._connection.isOpen()
        )

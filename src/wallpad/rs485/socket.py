import socket

from wallpad.rs485.base import ConnectionAdapter


class SocketAdapter(ConnectionAdapter):
    """ConnectionAdapter implementation for TCP socket communication."""

    def __init__(self, connection: socket.socket):
        self._connection = connection

    def read(self) -> bytes:
        return self._connection.recv(1)

    def write(self, data: bytes) -> int:
        return self._connection.send(data)

    def readable(self) -> bool:
        return True

    def is_open(self) -> bool:
        return self._connection is not None

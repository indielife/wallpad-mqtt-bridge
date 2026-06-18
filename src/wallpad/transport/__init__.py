from wallpad.transport.base import ConnectionAdapter
from wallpad.transport.rs485 import RS485
from wallpad.transport.serial import SerialAdapter
from wallpad.transport.socket import SocketAdapter

# New One
from .base import BaseTransport
from .serial import SerialTransport
from .socket import SocketTransport


def create(device_cfg: dict) -> BaseTransport:
    transport_type = device_cfg["transport"]
    if transport_type == "socket":
        return SocketTransport(device_cfg["host"], device_cfg["port"])
    elif transport_type == "serial":
        return SerialTransport(device_cfg["serial_port"], device_cfg["baud_rate"])
    raise ValueError(f"Unknown transport: {transport_type}")


__all__ = ["RS485", "ConnectionAdapter", "SerialAdapter", "SocketAdapter", "create"]

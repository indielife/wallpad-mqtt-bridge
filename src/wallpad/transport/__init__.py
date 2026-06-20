from wallpad.transport.base import ConnectionAdapter
from wallpad.transport.factory import (
    create_ventilator_adapters,
    create_wallpad_adapter,
)
from wallpad.transport.serial import SerialAdapter
from wallpad.transport.socket import SocketAdapter

from .base import BaseTransport
from .reconnect import ReconnectingTransport
from .serial import SerialTransport
from .socket import SocketTransport


def create(device_cfg: dict) -> BaseTransport:
    transport_type = device_cfg["transport"]
    if transport_type == "socket":
        return SocketTransport(device_cfg["host"], device_cfg["port"])
    elif transport_type == "serial":
        return SerialTransport(device_cfg["serial_port"], device_cfg["baud_rate"])
    raise ValueError(f"Unknown transport: {transport_type}")


__all__ = [
    "BaseTransport",
    "ConnectionAdapter",
    "ReconnectingTransport",
    "SerialAdapter",
    "SerialTransport",
    "SocketAdapter",
    "SocketTransport",
    "create",
    "create_ventilator_adapters",
    "create_wallpad_adapter",
]

from .base import BaseTransport
from .factory import create_panel_transport, create_ventilator_transports
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
    "ReconnectingTransport",
    "SerialTransport",
    "SocketTransport",
    "create",
    "create_panel_transport",
    "create_ventilator_transports",
]

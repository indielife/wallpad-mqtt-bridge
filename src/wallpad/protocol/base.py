from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class HardwareInfo:
    manufacturer: str
    model: str
    identifier_prefix: str
    name_prefix: str


class PacketParser(ABC):
    PACKET_FRAMES: ClassVar[dict[str, int]]

    @abstractmethod
    def validate_checksum(self, packet: str) -> tuple[bool, str]: ...

    @abstractmethod
    def parse_frame(self, packet: str) -> dict | None: ...

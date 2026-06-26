from abc import ABC, abstractmethod
from typing import ClassVar


class PacketParser(ABC):
    PACKET_FRAMES: ClassVar[dict[str, int]]

    @abstractmethod
    def validate_checksum(self, packet: str) -> tuple[bool, str]: ...

    @abstractmethod
    def parse_frame(self, packet: str) -> dict | None: ...

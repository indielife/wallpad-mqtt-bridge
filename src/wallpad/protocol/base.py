from abc import ABC, abstractmethod


class PacketParser(ABC):
    @abstractmethod
    def validate_checksum(self, packet: str) -> tuple[bool, str]: ...

    @abstractmethod
    def parse_frame(self, packet: str) -> dict: ...

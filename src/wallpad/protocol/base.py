from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class HardwareInfo:
    manufacturer: str
    model: str

    @property
    def slug(self) -> str:
        """식별자·표시 이름에 공통으로 쓰이는 제조사 소문자 슬러그입니다."""
        return self.manufacturer.lower()


class PacketParser(ABC):
    PACKET_FRAMES: ClassVar[dict[str, int]]

    @abstractmethod
    def validate_checksum(self, packet: str) -> tuple[bool, str]: ...

    @abstractmethod
    def parse_frame(self, packet: str) -> dict | None: ...

from abc import ABC, abstractmethod


class BaseTransport(ABC):
    @abstractmethod
    async def connect(self): ...

    @abstractmethod
    async def read(self, size: int) -> bytes: ...

    @abstractmethod
    async def write(self, data: bytes): ...

    @abstractmethod
    async def close(self): ...


class ConnectionAdapter(ABC):
    """Abstract base class defining the interface for RS485 communication adapters."""

    @abstractmethod
    def read(self) -> bytes:
        """Read 1 byte of data from the connection."""
        pass

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write bytes of data to the connection."""
        pass

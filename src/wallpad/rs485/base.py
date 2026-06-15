from abc import ABC, abstractmethod


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

    @abstractmethod
    def readable(self) -> bool:
        """Check if the connection is open/readable."""
        pass

    @abstractmethod
    def is_open(self) -> bool:
        """Check if the connection is currently open."""
        pass

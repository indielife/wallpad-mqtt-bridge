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

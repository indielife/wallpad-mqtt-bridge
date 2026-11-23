from abc import ABC, abstractmethod
from collections.abc import Callable

WriteCallback = Callable[[], None]


class BaseTransport(ABC):
    @abstractmethod
    async def connect(self): ...

    @abstractmethod
    async def read(self, size: int) -> bytes: ...

    @abstractmethod
    async def write(self, data: bytes, *, on_write: WriteCallback | None = None):
        """바이트를 쓴 직후, drain 대기 전에 on_write를 호출한다.

        재연결 후 다시 쓰는 경우에도 실제 쓰기마다 호출한다.
        """
        ...

    @abstractmethod
    async def close(self): ...

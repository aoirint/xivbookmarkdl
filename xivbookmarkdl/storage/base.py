from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from pathlib import Path


class Storage(ABC):
    @abstractmethod
    def download(self, key: str) -> AbstractAsyncContextManager[Path]: ...

    @abstractmethod
    async def upload(self, source_path: Path, dest_key: str) -> None: ...

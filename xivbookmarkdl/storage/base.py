from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import AsyncIterator


class StorageDownloadNotFoundError(Exception):
    pass


class Storage(ABC):
    @abstractmethod
    def iter_with_prefix(self, prefix: str) -> AsyncIterator[str]: ...

    @abstractmethod
    def download(self, key: str) -> AbstractAsyncContextManager[Path]: ...

    @abstractmethod
    async def upload(self, source_path: Path, dest_key: str) -> None: ...

import asyncio
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from .base import Storage, StorageDownloadNotFoundError


class StorageFilesystem(Storage):
    def __init__(
        self,
        root_dir: Path,
    ):
        self.root_dir = root_dir

    async def iter_with_prefix(self, prefix: str) -> AsyncIterator[str]:
        for p in self.root_dir.glob(f"{prefix}*"):
            yield str(p.relative_to(self.root_dir))

    @asynccontextmanager
    async def download(self, key: str) -> AsyncIterator[Path]:
        with TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            file = tmpdir / "a"

            try:
                await asyncio.to_thread(
                    shutil.copyfile,
                    self.root_dir / key,
                    file,
                )
            except FileNotFoundError as error:
                raise StorageDownloadNotFoundError from error

            yield file

    async def upload(self, source_path: Path, dest_key: str) -> None:
        dest_path = self.root_dir / dest_key

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(
            shutil.copyfile,
            source_path,
            dest_path,
        )

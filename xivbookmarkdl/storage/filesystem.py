import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import AsyncIterator

from .base import Storage


class StorageFilesystem(Storage):
    def __init__(
        self,
        root_dir: Path,
    ):
        self.root_dir = root_dir

    @asynccontextmanager
    async def download(self, key: str) -> AsyncIterator[Path]:
        with TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            file = tmpdir / "a"

            shutil.copyfile(self.root_dir / key, file)

            yield file

    async def upload(self, source_path: Path, dest_key: str) -> None:
        dest_path = self.root_dir / dest_key

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(source_path, dest_path)

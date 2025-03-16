from pathlib import Path

from ..storage.base import Storage

IMAGE_EXTS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp4",
    ".webm",
]


class IllustBinaryDao:
    def __init__(self, storage: Storage):
        self.storage = storage

    async def get_downloaded_illust_keys(
        self, illust_id: int, user_id: int
    ) -> list[str]:
        illust_prefix = f"{user_id}/{illust_id}/"

        keys: list[str] = []
        async for key in self.storage.iter_with_prefix(prefix=illust_prefix):
            if Path(key).suffix.lower() not in IMAGE_EXTS:
                continue

            keys.append(key)

        return keys

    async def store_illust_binary(
        self, illust_id: int, user_id: int, file: Path
    ) -> None:
        illust_key = f"{user_id}/{illust_id}/{file.name}"

        await self.storage.upload(source_path=file, dest_key=illust_key)

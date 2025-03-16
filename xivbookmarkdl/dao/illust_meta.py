import json
from datetime import UTC, datetime
from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pydantic import BaseModel

from ..storage.base import Storage, StorageDownloadNotFoundError

logger = getLogger(__name__)


class IllustMetaWithId(BaseModel):
    illust_id: int
    user_id: int
    illust: dict[str, Any]
    found_at: datetime | None
    updated_at: datetime | None


class IllustMeta(BaseModel):
    illust: dict[str, Any]
    found_at: datetime | None = None
    updated_at: datetime | None = None


class IllustMetaDao:
    def __init__(self, storage: Storage):
        self.storage = storage

    async def get_illust_meta(
        self,
        illust_id: int,
        user_id: int,
    ) -> IllustMetaWithId | None:
        meta_key = f"{user_id}/{illust_id}/illust.json"

        try:
            async with self.storage.download(key=meta_key) as meta_file:
                try:
                    illust_meta = IllustMeta.model_validate_json(
                        meta_file.read_text(encoding="utf-8")
                    )
                except Exception as inner_error:
                    logger.error(f"Failed to load illust meta: {meta_key}")
                    logger.exception(inner_error)

                    return None
        except StorageDownloadNotFoundError as outer_error:
            return None

        return IllustMetaWithId(
            illust_id=illust_id,
            user_id=user_id,
            illust=illust_meta.illust,
            found_at=illust_meta.found_at,
            updated_at=illust_meta.updated_at,
        )

    async def upsert_illust_meta(
        self,
        illust_id: int,
        user_id: int,
        illust: dict[str, Any],
        found_at: datetime,
    ) -> None:
        meta_key = f"{user_id}/{illust_id}/illust.json"

        found_at_utc = found_at.astimezone(UTC)

        old_meta = await self.get_illust_meta(illust_id=illust_id, user_id=user_id)
        if old_meta is not None and old_meta.found_at is not None:
            found_at_utc = old_meta.found_at.astimezone(UTC)

        with TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            meta_file = tmpdir / "illust.json"

            illust_meta = IllustMeta(
                illust=illust,
                found_at=found_at_utc,
                updated_at=datetime.now(tz=UTC),
            )

            with meta_file.open(mode="w", encoding="utf-8") as fp:
                json.dump(
                    illust_meta.model_dump(),
                    fp,
                    ensure_ascii=False,
                )

            await self.storage.upload(
                source_path=meta_file,
                dest_key=meta_key,
            )

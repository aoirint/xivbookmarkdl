import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import AsyncIterator

import boto3
from botocore.client import Config
from mypy_boto3_s3 import S3Client

from .base import Storage, StorageDownloadNotFoundError


class StorageS3(Storage):
    def __init__(
        self,
        bucket_name: str,
        aws_region: str | None,
        aws_endpoint_url: str | None,
        force_path_style: bool,
        aws_access_key_id: str | None,
        aws_secret_access_key: str | None,
        aws_session_token: str | None,
    ):
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.aws_endpoint_url = aws_endpoint_url
        self.force_path_style = force_path_style
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token

    def _create_s3_client(self) -> S3Client:
        return boto3.client(
            "s3",
            region_name=self.aws_region,
            endpoint_url=self.aws_endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            config=Config(
                s3={"addressing_style": "path" if self.force_path_style else "auto"}
            ),
        )

    @asynccontextmanager
    async def download(self, key: str) -> AsyncIterator[Path]:
        s3_client = self._create_s3_client()

        with TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            file = tmpdir / "a"

            try:
                await asyncio.to_thread(
                    s3_client.download_file,
                    Bucket=self.bucket_name,
                    Key=key,
                    Filename=str(file),
                )
            except s3_client.exceptions.NoSuchKey:
                # ファイルが存在しない場合、StorageDownloadNotFoundErrorをraiseする
                raise StorageDownloadNotFoundError

            yield file

    async def upload(self, source_path: Path, dest_key: str) -> None:
        s3_client = self._create_s3_client()

        await asyncio.to_thread(
            s3_client.upload_file,
            Filename=str(source_path),
            Bucket=self.bucket_name,
            Key=dest_key,
        )

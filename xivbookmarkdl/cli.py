import logging
import os
import time
from argparse import ArgumentParser, Namespace
from asyncio import iscoroutinefunction
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pixivpy3 import AppPixivAPI
from pydantic import BaseModel

from .dao.illust_binary import IllustBinaryDao
from .dao.illust_meta import IllustMetaDao
from .storage.filesystem import StorageFilesystem

UTC = timezone.utc
logger = logging.getLogger("xivbookmarkdl")


class BookmarkConfig(BaseModel):
    root_dir: Path
    refresh_token: str
    user_id: int
    recrawl: bool
    download_interval: float
    page_interval: float
    retry_interval: float


class SearchTagConfig(BaseModel):
    root_dir: Path
    refresh_token: str
    keyword: str
    recrawl: bool
    desc: bool
    download_interval: float
    page_interval: float
    retry_interval: float


async def download_illusts_desc(
    api: AppPixivAPI,
    first_result: Any,
    next_func: Any,
    illust_meta_dao: IllustMetaDao,
    illust_binary_dao: IllustBinaryDao,
    ignore_existence: bool,
    updated_at_utc: datetime,
    download_interval: float = 1.0,
    page_interval: float = 3.0,
    retry_interval: float = 10.0,
) -> None:
    result = first_result

    # search illusts in desc order
    new_illusts_desc: list[Any] = []
    while True:
        illusts = result.illusts
        page_new_illusts_desc: list[Any] = []

        for illust in illusts:
            user = illust.user

            if not ignore_existence:
                old_meta = await illust_meta_dao.get_illust_meta(
                    illust_id=int(illust.id), user_id=int(user.id)
                )
                if old_meta is not None:
                    downloaded_illust_keys = (
                        await illust_binary_dao.get_downloaded_illust_keys(
                            illust_id=int(illust.id),
                            user_id=int(user.id),
                        )
                    )

                    num_local_pages = len(downloaded_illust_keys)
                    num_remote_pages = (
                        1 if illust.meta_single_page else len(illust.meta_pages)
                    )

                    if num_local_pages == num_remote_pages:
                        continue

            page_new_illusts_desc.append(illust)

        # if no new illust in the current page, stop paging (desc search, asc download)
        if len(page_new_illusts_desc) == 0:
            print("No new illust found in page")
            break

        new_illusts_desc.extend(page_new_illusts_desc)
        print(f"Paging (found: {len(new_illusts_desc)})")

        next_qs = api.parse_qs(result.next_url)
        if not next_qs:
            break

        time.sleep(page_interval)

        for retry_index in range(3):
            next_result = next_func(**next_qs)
            if next_result.illusts is not None:
                break
            print(next_result)
            time.sleep(retry_interval * (retry_index + 1))

        result = next_result

    print(f"New Illusts: {len(new_illusts_desc)}")

    # download new illust in asc order
    new_illusts_asc = list(reversed(new_illusts_desc))
    for illust_index, illust in enumerate(new_illusts_asc):
        user = illust.user

        print(
            f"{illust_index}/{len(new_illusts_asc)}",
            user.id,
            user.name,
            illust.id,
            illust.title,
        )
        if illust.meta_single_page:
            image_url = illust.meta_single_page.original_image_url
            print(image_url)

            with TemporaryDirectory() as _tmpdir:
                tmpdir = Path(_tmpdir)

                if api.download(image_url, path=str(tmpdir)):
                    for file in tmpdir.iterdir():
                        await illust_binary_dao.store_illust_binary(
                            illust_id=int(illust.id),
                            user_id=int(user.id),
                            file=file,
                        )

                    time.sleep(download_interval)
        else:
            pages = illust.meta_pages
            for page in pages:
                image_url = page.image_urls.original
                print(image_url)

                with TemporaryDirectory() as _tmpdir:
                    tmpdir = Path(_tmpdir)

                    if api.download(image_url, path=str(tmpdir)):
                        for file in tmpdir.iterdir():
                            await illust_binary_dao.store_illust_binary(
                                illust_id=int(illust.id),
                                user_id=int(user.id),
                                file=file,
                            )

                        time.sleep(download_interval)

        await illust_meta_dao.upsert_illust_meta(
            illust_id=int(illust.id),
            user_id=int(user.id),
            illust=illust,
            found_at=updated_at_utc,
        )


async def download_illusts_asc(
    api: AppPixivAPI,
    first_result: Any,
    next_func: Any,
    illust_meta_dao: IllustMetaDao,
    illust_binary_dao: IllustBinaryDao,
    ignore_existence: bool,
    updated_at_utc: datetime,
    download_interval: float = 1.0,
    page_interval: float = 3.0,
    retry_interval: float = 10.0,
) -> None:

    # downloaded_user_ids = set([path.name for path in output_dir.iterdir()])
    # downloaded_user_illust_ids = set([(user_id, path.name) for user_id in downloaded_user_ids for path in Path(output_dir, user_id).iterdir()])  # noqa: B950
    # downloaded_illust_ids = set([illust_id for user_id, illust_id in downloaded_user_illust_ids])  # noqa: B950

    result = first_result

    # search and download illusts in asc order
    page_index = 0
    while True:
        illusts = result.illusts

        print(f"Page {page_index+1} (found: {len(illusts)})")

        for illust_index, illust in enumerate(illusts):
            user = illust.user

            if not ignore_existence:
                old_meta = await illust_meta_dao.get_illust_meta(
                    illust_id=int(illust.id), user_id=int(user.id)
                )
                if old_meta is not None:
                    downloaded_illust_keys = (
                        await illust_binary_dao.get_downloaded_illust_keys(
                            illust_id=int(illust.id),
                            user_id=int(user.id),
                        )
                    )

                    num_local_pages = len(downloaded_illust_keys)
                    num_remote_pages = (
                        1 if illust.meta_single_page else len(illust.meta_pages)
                    )

                    if num_local_pages == num_remote_pages:
                        continue

            print(
                f"Page {page_index+1}",
                f"Index {illust_index+1}/{len(illusts)}",
                user.id,
                user.name,
                illust.id,
                illust.title,
            )
            if illust.meta_single_page:
                image_url = illust.meta_single_page.original_image_url
                print(image_url)

                with TemporaryDirectory() as _tmpdir:
                    tmpdir = Path(_tmpdir)

                    if api.download(image_url, path=str(tmpdir)):
                        for file in tmpdir.iterdir():
                            await illust_binary_dao.store_illust_binary(
                                illust_id=int(illust.id),
                                user_id=int(user.id),
                                file=file,
                            )

                        time.sleep(download_interval)
            else:
                pages = illust.meta_pages
                for page in pages:
                    image_url = page.image_urls.original
                    print(image_url)

                    with TemporaryDirectory() as _tmpdir:
                        tmpdir = Path(_tmpdir)

                        if api.download(image_url, path=str(tmpdir)):
                            for file in tmpdir.iterdir():
                                await illust_binary_dao.store_illust_binary(
                                    illust_id=int(illust.id),
                                    user_id=int(user.id),
                                    file=file,
                                )

                            time.sleep(download_interval)

            await illust_meta_dao.upsert_illust_meta(
                illust_id=int(illust.id),
                user_id=int(user.id),
                illust=illust,
                found_at=updated_at_utc,
            )

        next_qs = api.parse_qs(result.next_url)
        if not next_qs:
            break

        time.sleep(page_interval)

        for retry_index in range(3):
            next_result = next_func(**next_qs)
            if next_result.illusts is not None:
                break
            print(next_result)
            time.sleep(retry_interval * (retry_index + 1))

        result = next_result
        page_index += 1


async def __run_bookmark(config: BookmarkConfig) -> None:
    api = AppPixivAPI()

    api.auth(refresh_token=config.refresh_token)

    illust_root_dir = Path(config.root_dir)

    illust_meta_dao = IllustMetaDao(
        storage=StorageFilesystem(root_dir=illust_root_dir),
    )

    illust_binary_dao = IllustBinaryDao(
        storage=StorageFilesystem(root_dir=illust_root_dir),
    )

    result = api.user_bookmarks_illust(user_id=config.user_id, req_auth=True)

    updated_at_utc = datetime.now(UTC)  # utc aware current time

    await download_illusts_desc(
        api=api,
        first_result=result,
        next_func=api.user_bookmarks_illust,
        illust_meta_dao=illust_meta_dao,
        illust_binary_dao=illust_binary_dao,
        ignore_existence=config.recrawl,
        updated_at_utc=updated_at_utc,
        download_interval=config.download_interval,
        page_interval=config.page_interval,
        retry_interval=config.retry_interval,
    )


async def run_bookmark(args: Namespace) -> None:
    await __run_bookmark(
        config=BookmarkConfig(
            root_dir=args.root_dir,
            refresh_token=args.refresh_token,
            user_id=args.user_id,
            recrawl=args.recrawl,
            download_interval=args.download_interval,
            page_interval=args.page_interval,
            retry_interval=args.retry_interval,
        )
    )


async def __run_search_tag(config: SearchTagConfig) -> None:
    api = AppPixivAPI()

    api.auth(refresh_token=config.refresh_token)

    illust_root_dir = Path(config.root_dir)

    illust_meta_dao = IllustMetaDao(
        storage=StorageFilesystem(root_dir=illust_root_dir),
    )

    illust_binary_dao = IllustBinaryDao(
        storage=StorageFilesystem(root_dir=illust_root_dir),
    )

    result = api.search_illust(
        word=config.keyword,
        search_target="exact_match_for_tags",
        sort="date_desc" if config.desc else "date_asc",
        req_auth=True,
    )

    updated_at_utc = datetime.now(UTC)  # utc aware current time

    download_func = download_illusts_asc
    if config.desc:
        download_func = download_illusts_desc

    await download_func(
        api=api,
        first_result=result,
        next_func=api.search_illust,
        illust_meta_dao=illust_meta_dao,
        illust_binary_dao=illust_binary_dao,
        ignore_existence=config.recrawl,
        updated_at_utc=updated_at_utc,
        download_interval=config.download_interval,
        page_interval=config.page_interval,
        retry_interval=config.retry_interval,
    )


async def run_search_tag(args: Namespace) -> None:
    await __run_search_tag(
        config=SearchTagConfig(
            root_dir=args.root_dir,
            refresh_token=args.refresh_token,
            keyword=args.keyword,
            recrawl=args.recrawl,
            desc=args.desc,
            download_interval=args.download_interval,
            page_interval=args.page_interval,
            retry_interval=args.retry_interval,
        )
    )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = ArgumentParser()

    subparsers = parser.add_subparsers()
    subparser_bookmark = subparsers.add_parser("bookmark")
    subparser_bookmark.add_argument(
        "--root_dir", type=Path, default=os.environ.get("XIVBKMDL_ROOT_DIR")
    )
    subparser_bookmark.add_argument(
        "--refresh_token", type=str, default=os.environ.get("XIVBKMDL_REFRESH_TOKEN")
    )
    subparser_bookmark.add_argument(
        "--user_id", type=int, default=os.environ.get("XIVBKMDL_USER_ID")
    )
    subparser_bookmark.add_argument("--recrawl", action="store_true")
    subparser_bookmark.add_argument(
        "--download_interval",
        type=float,
        default=os.environ.get("XIVBKMDL_DOWNLOAD_INTERVAL", "1.0"),
    )
    subparser_bookmark.add_argument(
        "--page_interval",
        type=float,
        default=os.environ.get("XIVBKMDL_PAGE_INTERVAL", "3.0"),
    )
    subparser_bookmark.add_argument(
        "--retry_interval",
        type=float,
        default=os.environ.get("XIVBKMDL_RETRY_INTERVAL", "10.0"),
    )
    subparser_bookmark.set_defaults(handler=run_bookmark)

    subparser_search_tag = subparsers.add_parser("search_tag")
    subparser_search_tag.add_argument(
        "--root_dir", type=Path, default=os.environ.get("XIVBKMDL_ROOT_DIR")
    )
    subparser_search_tag.add_argument(
        "--refresh_token", type=str, default=os.environ.get("XIVBKMDL_REFRESH_TOKEN")
    )
    subparser_search_tag.add_argument(
        "--keyword", type=str, default=os.environ.get("XIVBKMDL_KEYWORD")
    )
    subparser_search_tag.add_argument("--recrawl", action="store_true")
    subparser_search_tag.add_argument("--desc", action="store_true")
    subparser_search_tag.add_argument(
        "--download_interval",
        type=float,
        default=os.environ.get("XIVBKMDL_DOWNLOAD_INTERVAL", "1.0"),
    )
    subparser_search_tag.add_argument(
        "--page_interval",
        type=float,
        default=os.environ.get("XIVBKMDL_PAGE_INTERVAL", "3.0"),
    )
    subparser_search_tag.add_argument(
        "--retry_interval",
        type=float,
        default=os.environ.get("XIVBKMDL_RETRY_INTERVAL", "10.0"),
    )
    subparser_search_tag.set_defaults(handler=run_search_tag)

    args = parser.parse_args()

    if hasattr(args, "handler"):
        if iscoroutinefunction(args.handler):
            await args.handler(args)
        else:
            args.handler(args)
    else:
        parser.print_help()

import os
from pathlib import Path
from pixivpy3 import *
import time
import json
from datetime import datetime, timezone
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pydantic import BaseModel

UTC = timezone.utc

class BookmarkConfig(BaseModel):
  root_dir: Path
  refresh_token: str
  user_id: int
  recrawl: bool

@dataclass
class IllustMeta:
    illust_id: int
    user_id: int
    meta_dict: Dict[str, Any]
    fetched_at: datetime

class IllustMetaRepo(ABC):
    @abstractmethod
    def get_illust_meta(self) -> Optional[IllustMeta]:
        ...
    @abstractmethod
    def update_illust_meta(illust_meta: IllustMeta):
        ...

class FileIllustMetaRepo(IllustMetaRepo):
    def __init__(self, root_dir_path: Path):
        self.root_dir_path = root_dir_path

    def get_illust_meta(self, illust_id: int, user_id: int) -> Optional[IllustMeta]:
        illust_dir = Path(self.root_dir_path, str(user_id), str(illust_id))

        meta_path = illust_dir / 'illust.json'
        if not meta_path.exists():
            return None

        with open(meta_path, 'r', encoding='utf-8') as fp:
            try:
                illust_meta_dict = json.load(fp)
            except ValueError: # json.decoder.JSONDecodeError
                traceback.print_exc()
                return None

        return IllustMeta(
            illust_id=illust_id,
            user_id=user_id,
            meta_dict=illust_meta_dict['illust'],
            fetched_at=illust_meta_dict['found_at'],
        )

    def update_illust_meta(self, illust_meta: IllustMeta):
        illust_dir = Path(self.root_dir_path, str(illust_meta.user_id), str(illust_meta.illust_id))
        illust_dir.mkdir(exist_ok=True, parents=True)

        meta_path = illust_dir / 'illust.json'

        found_at_utc = illust_meta.fetched_at.astimezone(UTC)
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as fp:
                old_meta = {}

                try:
                    old_meta = json.load(fp)
                except ValueError: # json.decoder.JSONDecodeError
                    traceback.print_exc()

                if 'found_at' in old_meta:
                    found_at_utc = datetime.fromisoformat(old_meta['found_at']).astimezone(UTC)

        with open(meta_path, 'w', encoding='utf-8') as fp:
            json.dump({
                'illust': illust_meta.meta_dict,
                'found_at': found_at_utc.isoformat(),
                'updated_at': illust_meta.fetched_at.astimezone(UTC).isoformat(),
            }, fp, ensure_ascii=False)


def download_illusts(
    api: AppPixivAPI,
    output_dir: Path,
    first_result: Any,
    illust_meta_repo: IllustMetaRepo,
    ignore_existence: bool,
    updated_at_utc: datetime,
):
    IMAGE_EXTS = [
        '.jpg',
        '.jpeg',
        '.png',
        '.gif',
        '.webp',
        '.mp4',
        '.webm',
    ]

    # downloaded_user_ids = set([path.name for path in output_dir.iterdir()])
    # downloaded_user_illust_ids = set([(user_id, path.name) for user_id in downloaded_user_ids for path in Path(output_dir, user_id).iterdir()])
    # downloaded_illust_ids = set([illust_id for user_id, illust_id in downloaded_user_illust_ids])

    result = first_result

    # search illusts in desc order
    new_illusts_desc = []
    while True:
        illusts = result.illusts
        page_new_illusts_desc = []

        for illust in illusts:
            user = illust.user

            old_meta = illust_meta_repo.get_illust_meta(illust_id=int(illust.id), user_id=int(user.id))
            if old_meta is not None:
                illust_dir = Path(output_dir, str(user.id), str(illust.id))
                if illust_dir.exists() and not ignore_existence:
                    # Detect difference addition & download continuously
                    files_in_illust_dir = list(illust_dir.iterdir())

                    # remove program meta file, os meta file entries
                    images_in_illust_dir = list(filter(lambda path: path.suffix.lower() in IMAGE_EXTS, files_in_illust_dir))

                    num_local_pages = len(images_in_illust_dir)
                    num_remote_pages = 1 if illust.meta_single_page else len(illust.meta_pages)

                    if num_local_pages == num_remote_pages:
                        continue

            page_new_illusts_desc.append(illust)

        # if no new illust in the current page, stop paging (desc search, asc download)
        if len(page_new_illusts_desc) == 0:
            print('No new illust found in page')
            break

        new_illusts_desc.extend(page_new_illusts_desc)
        print(f'Paging (found: {len(new_illusts_desc)})')

        next_qs = api.parse_qs(result.next_url)
        if not next_qs:
            break

        time.sleep(1)
        result = api.user_bookmarks_illust(**next_qs)

    print(f'New Illusts: {len(new_illusts_desc)}')

    # download new illust in asc order
    new_illusts_asc = list(reversed(new_illusts_desc))
    for illust_index, illust in enumerate(new_illusts_asc):
        user = illust.user

        illust_dir = Path(output_dir, str(user.id), str(illust.id))
        illust_dir.mkdir(exist_ok=True, parents=True)

        print(f'{illust_index}/{len(new_illusts_asc)}', user.id, user.name, illust.id, illust.title)
        if illust.meta_single_page:
            image_url = illust.meta_single_page.original_image_url
            print(image_url)
            if api.download(image_url, path=illust_dir):
                time.sleep(1)
        else:
            pages = illust.meta_pages 
            for page in pages:
                image_url = page.image_urls.original
                print(image_url)
                if api.download(image_url, path=illust_dir):
                    time.sleep(1)

        illust_meta = IllustMeta(
            illust_id=int(illust.id),
            user_id=int(user.id),
            meta_dict=illust,
            fetched_at=updated_at_utc,
        )
        illust_meta_repo.update_illust_meta(illust_meta=illust_meta)


def __run_bookmark(config: BookmarkConfig):
    api = AppPixivAPI()

    api.auth(refresh_token=config.refresh_token)

    illust_root_dir = Path(config.root_dir)
    illust_meta_repo = FileIllustMetaRepo(root_dir_path=illust_root_dir)

    result = api.user_bookmarks_illust(user_id=config.user_id, req_auth=True)

    updated_at_utc = datetime.now(UTC) # utc aware current time

    download_illusts(
        api=api,
        output_dir=illust_root_dir,
        first_result=result,
        illust_meta_repo=illust_meta_repo,
        ignore_existence=config.recrawl,
        updated_at_utc=updated_at_utc,
    )


def run_bookmark(args):
    __run_bookmark(
        config=BookmarkConfig(
            root_dir=args.root_dir,
            refresh_token=args.refresh_token,
            user_id=args.user_id,
            recrawl=args.recrawl,
        )
    )


def main():
    import argparse
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()
    subparser_bookmark = subparsers.add_parser('bookmark')
    subparser_bookmark.add_argument('--root_dir', type=Path, default=os.environ.get('XIVBKMDL_ROOT_DIR'))
    subparser_bookmark.add_argument('--refresh_token', type=str, default=os.environ.get('XIVBKMDL_REFRESH_TOKEN'))
    subparser_bookmark.add_argument('--user_id', type=int, default=os.environ.get('XIVBKMDL_USER_ID'))
    subparser_bookmark.add_argument('--recrawl', action='store_true')
    subparser_bookmark.set_defaults(handler=run_bookmark)

    args = parser.parse_args()

    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

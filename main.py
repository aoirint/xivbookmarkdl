import os
from pathlib import Path
from dotenv import load_dotenv
from pixivpy3 import *
import time
import json
from datetime import datetime, timezone
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

load_dotenv()

REFRESH_TOKEN = os.environ['REFRESH_TOKEN']
USER_ID = os.environ['USER_ID']
ROOT_DIR = os.environ['ROOT_DIR']

UTC = timezone.utc

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
        illust_dir.mkdir(exist_ok=True, parents=True)

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


import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--recrawl', action='store_true')
args = parser.parse_args()

IGNORE_EXISTENCE = args.recrawl
IMAGE_EXTS = [
    '.jpg',
    '.jpeg',
    '.png',
    '.gif',
    '.webp',
    '.mp4',
    '.webm',
]

api = AppPixivAPI()

api.auth(refresh_token=REFRESH_TOKEN)

illust_root_dir = Path(ROOT_DIR)

illust_meta_repo = FileIllustMetaRepo(root_dir_path=illust_root_dir)

downloaded_user_ids = set([path.name for path in illust_root_dir.iterdir()])
downloaded_user_illust_ids = set([(user_id, path.name) for user_id in downloaded_user_ids for path in Path(illust_root_dir, user_id).iterdir()])
downloaded_illust_ids = set([illust_id for user_id, illust_id in downloaded_user_illust_ids])

result = api.user_bookmarks_illust(user_id=USER_ID, req_auth=True)

updated_at_utc = datetime.now(UTC) # utc aware current time

# search bookmarked illusts in desc order
new_illusts_desc = []
while True:
    illusts = result.illusts
    page_new_illusts_desc = []

    for illust in illusts:
        user = illust.user

        old_meta = illust_meta_repo.get_illust_meta(illust_id=int(illust.id), user_id=int(user.id))
        if old_meta is not None:
            illust_dir = Path(illust_root_dir, str(user.id), str(illust.id))
            if illust_dir.exists() and not IGNORE_EXISTENCE:
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

    illust_dir = Path(illust_root_dir, str(user.id), str(illust.id))
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

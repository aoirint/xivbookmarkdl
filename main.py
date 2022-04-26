import os
from pathlib import Path
from dotenv import load_dotenv
from pixivpy3 import *
import time

load_dotenv()

REFRESH_TOKEN = os.environ['REFRESH_TOKEN']
USER_ID = os.environ['USER_ID']
ROOT_DIR = os.environ['ROOT_DIR']

api = AppPixivAPI()

api.auth(refresh_token=REFRESH_TOKEN)

result = api.user_bookmarks_illust(user_id=USER_ID, req_auth=True)

while True:
    illusts = result.illusts

    for illust in illusts:
        pages = illust.meta_pages 
        user = illust.user

        illust_dir = Path(ROOT_DIR, str(user.id), str(illust.id))
        illust_dir.mkdir(exist_ok=True, parents=True)

        print(user.id, user.name)
        print(illust.id, illust.title)
        if illust.meta_single_page:
            image_url = illust.meta_single_page.original_image_url
            print(image_url)
            if api.download(image_url, path=illust_dir):
                time.sleep(1)
        else:
            for page in pages:
                image_url = page.image_urls.original
                print(image_url)
                if api.download(image_url, path=illust_dir):
                    time.sleep(1)

    next_qs = api.parse_qs(result.next_url)
    if not next_qs:
        break

    time.sleep(1)
    result = api.user_bookmarks_illust(**next_qs)


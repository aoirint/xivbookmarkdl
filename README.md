# xivbookmarkdl

- Python 3.10
- <https://github.com/upbit/pixivpy>


## Features

- Download bookmarked illusts in asc order by bookmarked time


## Usage

### 1. Build docker image

```shell
docker build -t aoirint/xivbookmarkdl .
```

### 2. Get Refresh Token

- <https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362>

### 3. Prepare a download directory

```shell
mkdir ./data
chown -R 1000:1000 ./data
```

### 4. Configure .env

```env
# .env

XIVBKMDL_REFRESH_TOKEN=
XIVBKMDL_USER_ID=
XIVBKMDL_ROOT_DIR=/data
```

## 5. Execute download

```shell
docker run --rm --env-file ./.env -v "./data:/data" aoirint/xivbookmarkdl
```


## Update requirements

```shell
pip3 install pip-tools
pip-compile requirements.in
```

# xivbookmarkdl

- Python 3.11
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

# Filesystem
XIVBKMDL_STORAGE_TYPE=filesystem
XIVBKMDL_ROOT_DIR=/data

# S3
# XIVBKMDL_STORAGE_TYPE=s3
# XIVBKMDL_ROOT_DIR=prefix/
# XIVBKMDL_STORAGE_S3_BUCKET=my-bucket
# XIVBKMDL_STORAGE_S3_REGION=local
# XIVBKMDL_STORAGE_S3_ENDPOINT_URL=http://127.0.0.1:9000
# XIVBKMDL_STORAGE_S3_FORCE_PATH_STYLE=true
# XIVBKMDL_STORAGE_S3_ACCESS_KEY_ID=
# XIVBKMDL_STORAGE_S3_SECRET_ACCESS_KEY=
# XIVBKMDL_STORAGE_S3_SESSION_TOKEN=
```

### 5. Execute download

```shell
docker run --rm --env-file ./.env -v "./data:/data" aoirint/xivbookmarkdl
```


## Development

### Dependency management

We use [Poetry](https://python-poetry.org/docs/#installation) as Python dependency manager.

```shell
poetry install

poetry update
```

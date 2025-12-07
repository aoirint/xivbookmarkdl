# xivbookmarkdl

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

### Setup

- Python 3.12
- uv 0.9

```shell
uv sync --frozen --all-groups
```

### Run

```shell
uv run python -m xivbookmarkdl
```

### Code format

```shell
uv run ruff check --fix
uv run ruff format

uv run mypy .
```

### Release

1. Bump version with `uv version <new_version>`.
2. Commit changes, create a pull request and merge into `main` branch.
3. GitHub Release and Docker image wlll be created automatically by GitHub Actions.

### GitHub Actions management

We use pinact to manage GitHub Actions versions.

- [pinact](https://github.com/suzuki-shunsuke/pinact)

```shell
# Lock
pinact run

# Update
pinact run --update
```

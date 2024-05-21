# syntax=docker/dockerfile:1.7
FROM python:3.11

ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN <<EOF
    set -eu

    apt-get update

    apt-get install -y \
        gosu

    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG CONTAINER_UID=1000
ARG CONTAINER_GID=1000
RUN <<EOF
    set -eu

    groupadd --non-unique --gid "${CONTAINER_GID}" user
    useradd --non-unique --uid "${CONTAINER_UID}" --gid "${CONTAINER_GID}" --create-home user
EOF

ADD ./requirements.txt /tmp/requirements.txt
RUN <<EOF
    set -eu

    gosu user pip3 install --no-cache-dir -r /tmp/requirements.txt
EOF

ADD ./xivbookmarkdl /opt/xivbookmarkdl

WORKDIR /opt/xivbookmarkdl
ENTRYPOINT [ "gosu", "user", "python3", "main.py" ]

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/milvus-runtime.env}"
IMAGE_TAR="${IMAGE_TAR:-}"
IMAGE_TAR_DIR="${IMAGE_TAR_DIR:-${SCRIPT_DIR}/dist}"
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/docker-compose.milvus.yml}"
DOCKER_VOLUME_DIRECTORY="${DOCKER_VOLUME_DIRECTORY:-${SCRIPT_DIR}/data}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"
MILVUS_GRPC_PORT="${MILVUS_GRPC_PORT:-19530}"
MILVUS_HTTP_PORT="${MILVUS_HTTP_PORT:-9091}"
MILVUS_NETWORK_NAME="${MILVUS_NETWORK_NAME:-milvus}"

if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${CONFIG_FILE}"
fi

IMAGE_TAR="${IMAGE_TAR:-}"
IMAGE_TAR_DIR="${IMAGE_TAR_DIR:-${SCRIPT_DIR}/dist}"
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/docker-compose.milvus.yml}"
DOCKER_VOLUME_DIRECTORY="${DOCKER_VOLUME_DIRECTORY:-${SCRIPT_DIR}/data}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"
MILVUS_GRPC_PORT="${MILVUS_GRPC_PORT:-19530}"
MILVUS_HTTP_PORT="${MILVUS_HTTP_PORT:-9091}"
MILVUS_NETWORK_NAME="${MILVUS_NETWORK_NAME:-milvus}"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "compose file not found: ${COMPOSE_FILE}"
  exit 1
fi

mkdir -p \
  "${DOCKER_VOLUME_DIRECTORY}/volumes/etcd" \
  "${DOCKER_VOLUME_DIRECTORY}/volumes/minio" \
  "${DOCKER_VOLUME_DIRECTORY}/volumes/milvus"

load_image_tars() {
  if [[ -n "${IMAGE_TAR}" ]]; then
    if [[ ! -f "${IMAGE_TAR}" ]]; then
      echo "image tar not found: ${IMAGE_TAR}"
      exit 1
    fi

    echo "loading image from ${IMAGE_TAR}"
    docker load -i "${IMAGE_TAR}"
    return
  fi

  if ! compgen -G "${IMAGE_TAR_DIR}/*.tar" >/dev/null 2>&1; then
    echo "no image tar files found in: ${IMAGE_TAR_DIR}"
    echo "set IMAGE_TAR=/path/to/file.tar or IMAGE_TAR_DIR=/path/to/tar-dir"
    exit 1
  fi

  for tar_file in "${IMAGE_TAR_DIR}"/*.tar; do
    echo "loading image from ${tar_file}"
    docker load -i "${tar_file}"
  done
}

load_image_tars

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose or docker-compose is required"
  exit 1
fi

export DOCKER_VOLUME_DIRECTORY
export MINIO_ACCESS_KEY
export MINIO_SECRET_KEY
export MINIO_API_PORT
export MINIO_CONSOLE_PORT
export MILVUS_GRPC_PORT
export MILVUS_HTTP_PORT
export MILVUS_NETWORK_NAME

"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" up -d

echo "milvus started"
echo "grpc:   127.0.0.1:${MILVUS_GRPC_PORT}"
echo "health: http://127.0.0.1:${MILVUS_HTTP_PORT}/healthz"
echo "minio:  http://127.0.0.1:${MINIO_CONSOLE_PORT}"

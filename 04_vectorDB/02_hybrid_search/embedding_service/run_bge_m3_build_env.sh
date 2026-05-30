#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-rag-in-one/bge-m3-embed:latest}"
IMAGE_TAR="${IMAGE_TAR:-}"
CONTAINER_NAME="${CONTAINER_NAME:-bge_m3_build_env}"
HOST_PORT="${HOST_PORT:-18080}"
GPU_DEVICE="${GPU_DEVICE:-0}"
EMBEDDING_DEVICE="${EMBEDDING_DEVICE:-cuda:0}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"
EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS:-128}"
EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS:-1}"
EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16:-true}"

if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
  if [[ -z "${IMAGE_TAR}" ]]; then
    echo "image not found locally: ${IMAGE_NAME}"
    echo "set IMAGE_TAR=/path/to/bge-m3-embed-latest.tar to load image before run"
    exit 1
  fi

  if [[ ! -f "${IMAGE_TAR}" ]]; then
    echo "image tar not found: ${IMAGE_TAR}"
    exit 1
  fi

  echo "loading image from tar: ${IMAGE_TAR}"
  docker load -i "${IMAGE_TAR}"
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  --gpus "device=${GPU_DEVICE}" \
  -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
  -e EMBEDDING_DEVICE="${EMBEDDING_DEVICE}" \
  -e EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16}" \
  -e EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE}" \
  -e EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS}" \
  -e EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS}" \
  -p "${HOST_PORT}:18080" \
  "${IMAGE_NAME}"

echo "container started: ${CONTAINER_NAME}"
echo "healthz: http://127.0.0.1:${HOST_PORT}/healthz"
echo "readyz:  http://127.0.0.1:${HOST_PORT}/readyz"
echo "logs:    docker logs -f ${CONTAINER_NAME}"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/docker-runtime.env}"

IMAGE_NAME="${IMAGE_NAME:-rag-in-one/bge-m3-embed:latest}"
IMAGE_TAR="${IMAGE_TAR:-}"
GPU_DEVICES="${GPU_DEVICES:-all}"
CONTAINER_PREFIX="${CONTAINER_PREFIX:-bge_m3}"
HOST_PORT_BASE="${HOST_PORT_BASE:-18080}"
EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16:-true}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"
EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS:-128}"
EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS:-1}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${CONFIG_FILE}"
fi

IMAGE_NAME="${IMAGE_NAME:-rag-in-one/bge-m3-embed:latest}"
IMAGE_TAR="${IMAGE_TAR:-}"
GPU_DEVICES="${GPU_DEVICES:-all}"
CONTAINER_PREFIX="${CONTAINER_PREFIX:-bge_m3}"
HOST_PORT_BASE="${HOST_PORT_BASE:-18080}"
EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16:-true}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"
EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS:-128}"
EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS:-1}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

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

resolve_gpu_devices() {
  if [[ "${GPU_DEVICES}" == "all" ]]; then
    nvidia-smi --query-gpu=index --format=csv,noheader | tr -d ' ' | paste -sd, -
  else
    echo "${GPU_DEVICES}"
  fi
}

GPU_LIST="$(resolve_gpu_devices)"
if [[ -z "${GPU_LIST}" ]]; then
  echo "no gpu devices resolved"
  exit 1
fi

IFS=',' read -r -a GPU_ARRAY <<< "${GPU_LIST}"

for gpu in "${GPU_ARRAY[@]}"; do
  if [[ ! "${gpu}" =~ ^[0-9]+$ ]]; then
    echo "invalid gpu id: ${gpu}"
    exit 1
  fi
done

for index in "${!GPU_ARRAY[@]}"; do
  gpu="${GPU_ARRAY[$index]}"
  host_port="$((HOST_PORT_BASE + index))"
  container_name="${CONTAINER_PREFIX}_gpu${gpu}"

  docker rm -f "${container_name}" >/dev/null 2>&1 || true

  docker run -d \
    --name "${container_name}" \
    --restart unless-stopped \
    --gpus "device=${gpu}" \
    -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
    -e EMBEDDING_DEVICE="cuda:0" \
    -e EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16}" \
    -e EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE}" \
    -e EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS}" \
    -e EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS}" \
    -e LOG_LEVEL="${LOG_LEVEL}" \
    -p "${host_port}:18080" \
    "${IMAGE_NAME}"

  echo "started ${container_name} on gpu=${gpu} port=${host_port}"
done

echo "done"
echo "gpu_devices=${GPU_LIST}"

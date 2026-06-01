#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-${SCRIPT_DIR}/docker-runtime.env}"

IMAGE_NAME="${IMAGE_NAME:-rag-in-one/bge-m3-embed:latest}"
IMAGE_TAR="${IMAGE_TAR:-}"
GPU_DEVICES="${GPU_DEVICES:-all}"
DOCKER_GPU_MODE="${DOCKER_GPU_MODE:-gpus}"
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
DOCKER_GPU_MODE="${DOCKER_GPU_MODE:-gpus}"
CONTAINER_PREFIX="${CONTAINER_PREFIX:-bge_m3}"
HOST_PORT_BASE="${HOST_PORT_BASE:-18080}"
EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16:-true}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"
EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS:-128}"
EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS:-1}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found"
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi command not found"
  echo "install NVIDIA driver first, then verify the host can see GPUs with: nvidia-smi"
  exit 1
fi

case "${DOCKER_GPU_MODE}" in
  gpus | runtime | cdi)
    ;;
  *)
    echo "invalid DOCKER_GPU_MODE: ${DOCKER_GPU_MODE}"
    echo "supported values: gpus, runtime, cdi"
    exit 1
    ;;
esac

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

print_gpu_runtime_hint() {
  local container_name="$1"
  local gpu="$2"

  cat <<EOF
failed to start ${container_name} on gpu=${gpu}

This usually means Docker cannot expose NVIDIA GPUs to containers yet.
Run these checks on the production host:

  nvidia-smi
  command -v nvidia-ctk
  docker run --rm --gpus all ${IMAGE_NAME} python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"

If the Docker GPU check fails with a CDI/vendor error, configure NVIDIA Container Toolkit for Docker and restart Docker:

  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker

If this host intentionally uses Docker CDI mode, generate and verify the CDI spec, then rerun with DOCKER_GPU_MODE=cdi:

  sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
  nvidia-ctk cdi list
  DOCKER_GPU_MODE=cdi ${BASH_SOURCE[0]}

If this host uses the legacy NVIDIA runtime path, rerun with DOCKER_GPU_MODE=runtime:

  DOCKER_GPU_MODE=runtime ${BASH_SOURCE[0]}
EOF
}

docker_gpu_args() {
  local gpu="$1"

  case "${DOCKER_GPU_MODE}" in
    gpus)
      echo "--gpus"
      echo "device=${gpu}"
      ;;
    runtime)
      echo "--runtime"
      echo "nvidia"
      echo "-e"
      echo "NVIDIA_VISIBLE_DEVICES=${gpu}"
      ;;
    cdi)
      echo "--device"
      echo "nvidia.com/gpu=${gpu}"
      ;;
    *)
      echo "invalid DOCKER_GPU_MODE: ${DOCKER_GPU_MODE}" >&2
      echo "supported values: gpus, runtime, cdi" >&2
      return 1
      ;;
  esac
}

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

  gpu_args=()
  while IFS= read -r arg; do
    gpu_args+=("${arg}")
  done < <(docker_gpu_args "${gpu}")

  docker_cmd=(
    docker run -d
    --name "${container_name}" \
    --restart unless-stopped \
    "${gpu_args[@]}" \
    -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
    -e EMBEDDING_DEVICE="cuda:0" \
    -e EMBEDDING_USE_FP16="${EMBEDDING_USE_FP16}" \
    -e EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE}" \
    -e EMBEDDING_MAX_TEXTS="${EMBEDDING_MAX_TEXTS}" \
    -e EMBEDDING_MAX_CONCURRENT_REQUESTS="${EMBEDDING_MAX_CONCURRENT_REQUESTS}" \
    -e LOG_LEVEL="${LOG_LEVEL}" \
    -p "${host_port}:18080" \
    "${IMAGE_NAME}"
  )

  if ! "${docker_cmd[@]}"; then
    print_gpu_runtime_hint "${container_name}" "${gpu}"
    exit 1
  fi

  echo "started ${container_name} on gpu=${gpu} port=${host_port} docker_gpu_mode=${DOCKER_GPU_MODE}"
done

echo "done"
echo "gpu_devices=${GPU_LIST}"

#!/usr/bin/env bash
set -euo pipefail

MILVUS_IMAGE="${MILVUS_IMAGE:-milvusdb/milvus:v2.6.17}"
ETCD_IMAGE="${ETCD_IMAGE:-quay.io/coreos/etcd:v3.5.25}"
MINIO_IMAGE="${MINIO_IMAGE:-minio/minio:RELEASE.2024-05-28T17-19-04Z}"
PLATFORM="${PLATFORM:-linux/amd64}"

OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist}"
OUTPUT_FILE="${OUTPUT_FILE:-milvus-v2.6.17-offline-images.tar}"

mkdir -p "${OUTPUT_DIR}"

check_image_size() {
  local image="$1"
  local min_size_bytes="$2"
  local size
  size="$(docker image inspect --format '{{.Size}}' "${image}")"

  if [[ -z "${size}" ]]; then
    echo "failed to inspect image size: ${image}"
    exit 1
  fi

  if (( size < min_size_bytes )); then
    echo "image size check failed for ${image}: ${size} bytes is smaller than expected"
    echo "this usually means the pulled image is incomplete or not the target platform image"
    exit 1
  fi

  echo "checked ${image}: ${size} bytes"
}

ensure_image() {
  local image="$1"
  if docker image inspect "${image}" >/dev/null 2>&1; then
    echo "using existing local image: ${image}"
    return
  fi

  echo "pulling image: ${image} platform=${PLATFORM}"
  docker pull --platform "${PLATFORM}" "${image}"
}

ensure_image "${MILVUS_IMAGE}"
ensure_image "${ETCD_IMAGE}"
ensure_image "${MINIO_IMAGE}"

# Rough lower bounds to catch obviously broken pulls.
check_image_size "${MILVUS_IMAGE}" 100000000
check_image_size "${ETCD_IMAGE}" 20000000
check_image_size "${MINIO_IMAGE}" 50000000

echo "saving images to ${OUTPUT_DIR}/${OUTPUT_FILE}"
docker save -o "${OUTPUT_DIR}/${OUTPUT_FILE}" \
  "${MILVUS_IMAGE}" \
  "${ETCD_IMAGE}" \
  "${MINIO_IMAGE}"

echo "saved:"
ls -lh "${OUTPUT_DIR}/${OUTPUT_FILE}"

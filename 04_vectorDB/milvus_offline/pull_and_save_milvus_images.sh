#!/usr/bin/env bash
set -euo pipefail

MILVUS_IMAGE="${MILVUS_IMAGE:-milvusdb/milvus:v2.6.17}"
ETCD_IMAGE="${ETCD_IMAGE:-quay.io/coreos/etcd:v3.5.25}"
MINIO_IMAGE="${MINIO_IMAGE:-minio/minio:RELEASE.2024-05-28T17-19-04Z}"
PLATFORM="${PLATFORM:-linux/amd64}"

OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist}"
EXPORT_MODE="${EXPORT_MODE:-buildx}"
COMBINED_OUTPUT_FILE="${COMBINED_OUTPUT_FILE:-milvus-v2.6.17-offline-images.tar}"

MILVUS_TAR="${MILVUS_TAR:-milvus-v2.6.17.tar}"
ETCD_TAR="${ETCD_TAR:-etcd-v3.5.25.tar}"
MINIO_TAR="${MINIO_TAR:-minio-RELEASE.2024-05-28T17-19-04Z.tar}"

mkdir -p "${OUTPUT_DIR}"

check_tar_size() {
  local tar_file="$1"
  local min_size_bytes="$2"
  local size

  size="$(wc -c < "${tar_file}")"
  if (( size < min_size_bytes )); then
    echo "tar size check failed: ${tar_file} is only ${size} bytes"
    echo "this tar is too small to contain a usable image"
    exit 1
  fi

  echo "checked tar file: ${tar_file} ${size} bytes"
}

export_one_with_buildx() {
  local image="$1"
  local output_file="$2"
  local min_size_bytes="$3"
  local tmpdir

  if ! docker buildx version >/dev/null 2>&1; then
    echo "docker buildx is required for EXPORT_MODE=buildx"
    exit 1
  fi

  tmpdir="$(mktemp -d)"
  printf 'FROM %s\n' "${image}" > "${tmpdir}/Dockerfile"

  echo "exporting ${image} platform=${PLATFORM} to ${output_file}"
  docker buildx build \
    --platform "${PLATFORM}" \
    -t "${image}" \
    --output "type=docker,dest=${output_file}" \
    "${tmpdir}"

  rm -rf "${tmpdir}"
  check_tar_size "${output_file}" "${min_size_bytes}"
}

pull_if_missing() {
  local image="$1"

  if docker image inspect "${image}" >/dev/null 2>&1; then
    echo "using existing local image: ${image}"
    return
  fi

  echo "pulling image: ${image} platform=${PLATFORM}"
  docker pull --platform "${PLATFORM}" "${image}"
}

export_with_docker_save() {
  local output_file="${OUTPUT_DIR}/${COMBINED_OUTPUT_FILE}"

  pull_if_missing "${MILVUS_IMAGE}"
  pull_if_missing "${ETCD_IMAGE}"
  pull_if_missing "${MINIO_IMAGE}"

  echo "saving images to ${output_file}"
  docker save -o "${output_file}" \
    "${MILVUS_IMAGE}" \
    "${ETCD_IMAGE}" \
    "${MINIO_IMAGE}"

  check_tar_size "${output_file}" 200000000
}

case "${EXPORT_MODE}" in
  buildx)
    export_one_with_buildx "${MILVUS_IMAGE}" "${OUTPUT_DIR}/${MILVUS_TAR}" 100000000
    export_one_with_buildx "${ETCD_IMAGE}" "${OUTPUT_DIR}/${ETCD_TAR}" 20000000
    export_one_with_buildx "${MINIO_IMAGE}" "${OUTPUT_DIR}/${MINIO_TAR}" 50000000
    ;;
  save)
    export_with_docker_save
    ;;
  *)
    echo "unsupported EXPORT_MODE: ${EXPORT_MODE}"
    echo "supported values: buildx, save"
    exit 1
    ;;
esac

echo "exported files:"
ls -lh "${OUTPUT_DIR}"/*.tar

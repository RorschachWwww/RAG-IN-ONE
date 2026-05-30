#!/usr/bin/env bash
set -euo pipefail

MILVUS_IMAGE="${MILVUS_IMAGE:-milvusdb/milvus:v2.6.17}"
ETCD_IMAGE="${ETCD_IMAGE:-quay.io/coreos/etcd:v3.5.25}"
MINIO_IMAGE="${MINIO_IMAGE:-minio/minio:RELEASE.2024-05-28T17-19-04Z}"

OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist}"
OUTPUT_FILE="${OUTPUT_FILE:-milvus-v2.6.17-offline-images.tar}"

mkdir -p "${OUTPUT_DIR}"

echo "pulling images..."
docker pull "${MILVUS_IMAGE}"
docker pull "${ETCD_IMAGE}"
docker pull "${MINIO_IMAGE}"

echo "saving images to ${OUTPUT_DIR}/${OUTPUT_FILE}"
docker save -o "${OUTPUT_DIR}/${OUTPUT_FILE}" \
  "${MILVUS_IMAGE}" \
  "${ETCD_IMAGE}" \
  "${MINIO_IMAGE}"

echo "saved:"
ls -lh "${OUTPUT_DIR}/${OUTPUT_FILE}"

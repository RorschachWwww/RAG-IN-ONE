#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-rag-in-one/bge-m3-embed:latest}"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist}"
OUTPUT_FILE="${OUTPUT_FILE:-bge-m3-embed-latest.tar}"

mkdir -p "${OUTPUT_DIR}"

echo "saving image: ${IMAGE_NAME}"
docker image inspect "${IMAGE_NAME}" >/dev/null

docker save -o "${OUTPUT_DIR}/${OUTPUT_FILE}" "${IMAGE_NAME}"

echo "saved to: ${OUTPUT_DIR}/${OUTPUT_FILE}"
ls -lh "${OUTPUT_DIR}/${OUTPUT_FILE}"

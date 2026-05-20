#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-rag-in-one/bge-m3-embed:latest}"

docker rm -f bge_m3_gpu0 bge_m3_gpu1 >/dev/null 2>&1 || true

docker run -d \
  --name bge_m3_gpu0 \
  --restart unless-stopped \
  --gpus '"device=0"' \
  -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
  -e CUDA_VISIBLE_DEVICES=0 \
  -e EMBEDDING_DEVICE=cuda:0 \
  -e EMBEDDING_USE_FP16=true \
  -e EMBEDDING_BATCH_SIZE=32 \
  -e EMBEDDING_MAX_TEXTS=128 \
  -e EMBEDDING_MAX_CONCURRENT_REQUESTS=1 \
  -p 18080:18080 \
  "${IMAGE_NAME}"

docker run -d \
  --name bge_m3_gpu1 \
  --restart unless-stopped \
  --gpus '"device=1"' \
  -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
  -e CUDA_VISIBLE_DEVICES=1 \
  -e EMBEDDING_DEVICE=cuda:0 \
  -e EMBEDDING_USE_FP16=true \
  -e EMBEDDING_BATCH_SIZE=32 \
  -e EMBEDDING_MAX_TEXTS=128 \
  -e EMBEDDING_MAX_CONCURRENT_REQUESTS=1 \
  -p 18081:18080 \
  "${IMAGE_NAME}"

echo "started:"
echo "  gpu0 -> http://<host>:18080"
echo "  gpu1 -> http://<host>:18081"

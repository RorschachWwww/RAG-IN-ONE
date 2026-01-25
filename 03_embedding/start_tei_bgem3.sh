#!/bin/bash

# 定义变量，方便后续调整
MODEL_ID="BAAI/bge-m3"
VOLUME_PATH="$PWD/data"
PORT=8080

echo "正在启动 TEI 服务，模型: $MODEL_ID ..."

# 停止并删除旧容器（如果存在），防止端口冲突
docker rm -f tei-bge-m3 2>/dev/null

# 启动新容器
docker run -d --gpus all \
    -p $PORT:80 \
    -v $VOLUME_PATH:/data \
    --name tei-bge-m3 \
    --restart always \
    --pull always \
    ghcr.io/huggingface/text-embeddings-inference:latest \
    --model-id $MODEL_ID \
    --dtype float16 \
    --max-client-batch-size 32 \
    --max-batch-tokens 16384

echo "服务已启动，监听端口: $PORT"
echo "日志查看命令: docker logs -f tei-bge-m3"
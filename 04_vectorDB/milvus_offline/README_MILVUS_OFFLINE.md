# Milvus 离线镜像与生产部署

这套文件面向两个环境：

- 构建环境：可以连公网，用来拉取镜像并导出 tar
- 生产环境：无法连公网，用来导入 tar 并启动 Milvus

使用的镜像版本：

| 组件 | Docker 镜像 |
| --- | --- |
| Milvus | `milvusdb/milvus:v2.6.17` |
| etcd | `quay.io/coreos/etcd:v3.5.25` |
| MinIO | `minio/minio:RELEASE.2024-05-28T17-19-04Z` |

相关文件：

- [pull_and_save_milvus_images.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/pull_and_save_milvus_images.sh)
- [import_and_run_milvus.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/import_and_run_milvus.sh)
- [docker-compose.milvus.yml](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/docker-compose.milvus.yml)

## 1. 在构建环境拉取并导出镜像

执行：

```bash
chmod +x /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/pull_and_save_milvus_images.sh
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/pull_and_save_milvus_images.sh
```

默认会生成一个合并 tar：

```bash
dist/milvus-v2.6.17-offline-images.tar
```

如果你想改导出目录或文件名：

```bash
OUTPUT_DIR=/tmp OUTPUT_FILE=milvus-offline-20260530.tar \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/pull_and_save_milvus_images.sh
```

## 2. 把 tar 拷贝到生产环境

把以下文件一起拷贝到生产环境一台机器上：

- 镜像 tar 文件
- [import_and_run_milvus.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/import_and_run_milvus.sh)
- [docker-compose.milvus.yml](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/docker-compose.milvus.yml)

## 3. 在生产环境导入并启动 Milvus

执行：

```bash
chmod +x /path/to/import_and_run_milvus.sh
IMAGE_TAR=/path/to/milvus-v2.6.17-offline-images.tar \
/path/to/import_and_run_milvus.sh
```

脚本会自动做这些事：

- `docker load` 导入镜像
- 创建本地数据目录
- 用 `docker compose` 启动 `etcd`、`minio`、`milvus-standalone`

默认端口：

- Milvus gRPC: `19530`
- Milvus health/http: `9091`
- MinIO API: `9000`
- MinIO Console: `9001`

## 4. 可选配置

如果你想改数据目录：

```bash
DOCKER_VOLUME_DIRECTORY=/data/milvus \
IMAGE_TAR=/path/to/milvus-v2.6.17-offline-images.tar \
/path/to/import_and_run_milvus.sh
```

如果你想改端口：

```bash
MILVUS_GRPC_PORT=19531 \
MILVUS_HTTP_PORT=9092 \
MINIO_API_PORT=9002 \
MINIO_CONSOLE_PORT=9003 \
IMAGE_TAR=/path/to/milvus-v2.6.17-offline-images.tar \
/path/to/import_and_run_milvus.sh
```

如果你想改 MinIO 凭据：

```bash
MINIO_ACCESS_KEY=your-access-key \
MINIO_SECRET_KEY=your-secret-key \
IMAGE_TAR=/path/to/milvus-v2.6.17-offline-images.tar \
/path/to/import_and_run_milvus.sh
```

## 5. 健康检查

Milvus：

```bash
curl http://127.0.0.1:9091/healthz
```

查看容器：

```bash
docker ps
```

查看日志：

```bash
docker logs -f milvus-standalone
docker logs -f milvus-etcd
docker logs -f milvus-minio
```

## 6. 停止服务

在 `docker-compose.milvus.yml` 所在目录执行：

```bash
docker compose -f docker-compose.milvus.yml down
```

## 7. 说明

这份 compose 结构参考了 Milvus 官方 standalone Docker Compose 的服务关系和组件版本约束，并把镜像版本固定成了你指定的版本组合：

- [Milvus 官方 standalone compose 参考](https://github.com/milvus-io/milvus/blob/master/deployments/docker/standalone/docker-compose.yml)

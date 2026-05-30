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
- [milvus-runtime.env](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/milvus-runtime.env)

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

推荐先编辑运行时配置文件：

```bash
vi /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/milvus_offline/milvus-runtime.env
```

建议至少把数据目录改成你们生产机的固定路径，例如：

```bash
DOCKER_VOLUME_DIRECTORY=/data/milvus-offline
```

执行：

```bash
chmod +x /path/to/import_and_run_milvus.sh
IMAGE_TAR=/path/to/milvus-v2.6.17-offline-images.tar \
/path/to/import_and_run_milvus.sh
```

如果你已经在 `milvus-runtime.env` 里写好了 `IMAGE_TAR`，那直接执行脚本即可：

```bash
chmod +x /path/to/import_and_run_milvus.sh
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

如果你想临时覆盖配置文件里的数据目录：

```bash
DOCKER_VOLUME_DIRECTORY=/data/milvus \
IMAGE_TAR=/path/to/milvus-v2.6.17-offline-images.tar \
/path/to/import_and_run_milvus.sh
```

但更推荐的方式是直接改 `milvus-runtime.env`，这样以后每次启动都不用重复写。

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

## 5. 镜像已经加载时，如何一键拉起

如果你的生产环境里这 3 个镜像都已经提前 `docker load` 过了：

- `milvusdb/milvus:v2.6.17`
- `quay.io/coreos/etcd:v3.5.25`
- `minio/minio:RELEASE.2024-05-28T17-19-04Z`

那么不需要再执行 `docker load`，可以直接用 compose 一键拉起。

先进入 `docker-compose.milvus.yml` 所在目录：

```bash
cd /path/to/04_vectorDB/milvus_offline
```

最简单的启动方式：

```bash
docker compose -f docker-compose.milvus.yml up -d
```

如果你的环境里是老版本 `docker-compose`：

```bash
docker-compose -f docker-compose.milvus.yml up -d
```

这会直接启动：

- `milvus-etcd`
- `milvus-minio`
- `milvus-standalone`

默认会优先读取 `milvus-runtime.env` 里的 `DOCKER_VOLUME_DIRECTORY`。

如果你没有改配置文件，才会退回到脚本目录下的 `data`。

所以更推荐在配置文件里显式指定固定数据目录，避免将来换目录后找不到数据：

```bash
cd /path/to/04_vectorDB/milvus_offline
mkdir -p /data/milvus-offline/volumes/etcd /data/milvus-offline/volumes/minio /data/milvus-offline/volumes/milvus

DOCKER_VOLUME_DIRECTORY=/data/milvus-offline \
docker compose -f docker-compose.milvus.yml up -d
```

如果你还想同时改端口或 MinIO 账号，也可以一条命令带上：

```bash
DOCKER_VOLUME_DIRECTORY=/data/milvus-offline \
MILVUS_GRPC_PORT=19531 \
MILVUS_HTTP_PORT=9092 \
MINIO_API_PORT=9002 \
MINIO_CONSOLE_PORT=9003 \
MINIO_ACCESS_KEY=your-access-key \
MINIO_SECRET_KEY=your-secret-key \
docker compose -f docker-compose.milvus.yml up -d
```

如果你想确认镜像确实都已经在本机：

```bash
docker image inspect milvusdb/milvus:v2.6.17
docker image inspect quay.io/coreos/etcd:v3.5.25
docker image inspect minio/minio:RELEASE.2024-05-28T17-19-04Z
```

这套方式适合“镜像已经在生产机上，只差把服务起起来”的场景。

## 6. 健康检查

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

## 7. 停止服务

在 `docker-compose.milvus.yml` 所在目录执行：

```bash
docker compose -f docker-compose.milvus.yml down
```

如果你启动时指定过环境变量，停止时不需要重复带上；容器名是固定的：

- `milvus-etcd`
- `milvus-minio`
- `milvus-standalone`

## 8. systemd 开机自启

如果你希望生产机重启后自动拉起 Milvus，推荐给这套 compose 配一个 `systemd` 服务。

先确认以下目录和文件已经固定好位置：

- `docker-compose.milvus.yml`
- Milvus 数据目录，例如 `/data/milvus-offline`

下面给出一个示例服务文件：

```ini
[Unit]
Description=Milvus Offline Standalone
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/04_vectorDB/milvus_offline
Environment=DOCKER_VOLUME_DIRECTORY=/data/milvus-offline
ExecStart=/usr/bin/docker compose -f docker-compose.milvus.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.milvus.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

把它保存为：

```bash
/etc/systemd/system/milvus-offline.service
```

然后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable milvus-offline
sudo systemctl start milvus-offline
```

查看状态：

```bash
sudo systemctl status milvus-offline
docker ps
```

如果你的宿主机没有 `docker compose` 子命令，只有老版本 `docker-compose`，可以把服务文件里的启动命令改成：

```ini
ExecStart=/usr/bin/docker-compose -f docker-compose.milvus.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.milvus.yml down
```

如果你启动时还需要固定端口、MinIO 账号等配置，也可以继续在服务文件里加环境变量：

```ini
Environment=DOCKER_VOLUME_DIRECTORY=/data/milvus-offline
Environment=MILVUS_GRPC_PORT=19530
Environment=MILVUS_HTTP_PORT=9091
Environment=MINIO_API_PORT=9000
Environment=MINIO_CONSOLE_PORT=9001
Environment=MINIO_ACCESS_KEY=minioadmin
Environment=MINIO_SECRET_KEY=minioadmin
```

如果后续修改了 compose 文件或 systemd 服务文件，记得执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart milvus-offline
```

如果你想取消开机自启：

```bash
sudo systemctl disable milvus-offline
sudo systemctl stop milvus-offline
```

## 9. 说明

这份 compose 结构参考了 Milvus 官方 standalone Docker Compose 的服务关系和组件版本约束，并把镜像版本固定成了你指定的版本组合：

- [Milvus 官方 standalone compose 参考](https://github.com/milvus-io/milvus/blob/master/deployments/docker/standalone/docker-compose.yml)

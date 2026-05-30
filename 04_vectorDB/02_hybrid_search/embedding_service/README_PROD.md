# BGE-M3 离线生产部署方案

这个方案面向如下场景：

- 构建环境可以联网
- 生产环境不能联网
- 生产环境有多张 NVIDIA GPU，例如 2 张 T4
- 希望把 `bge-m3` 做成长期运行的 embedding 服务

## 总体方案

推荐方案是：

1. 在联网的构建环境里构建 Docker 镜像
2. 构建时把 `BAAI/bge-m3` 模型权重直接下载进镜像
3. 把镜像 `docker save` 成 tar 包
4. 把 tar 包拷贝到生产环境
5. 在生产环境 `docker load`
6. 按 GPU 数量起多个容器，每个容器绑定 1 张 GPU

这样做的好处：

- 生产环境完全不依赖外网
- 每张 GPU 一个服务进程，资源边界清晰
- 比单进程同时“看见两张卡”更容易排障和扩容
- 升级、回滚都更简单

## 为什么不建议直接用当前 `embedding_service.py` 进生产

当前的 `embedding_service.py` 更适合开发和验证，主要有这些生产化优化空间：

- 错误响应会把 traceback 直接返回给调用方，不适合生产暴露
- 批大小、并发数、模型路径等配置不够环境化
- 缺少更明确的 `healthz` / `readyz` 分离
- 没有限制同一进程内的并发 encode，容易在高峰时把单卡显存打爆
- 更适合“每 GPU 一个进程”的部署方式，而不是一个进程同时管理多卡

所以这里额外提供了一个生产版服务：

- [embedding_service_prod.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/embedding_service_prod.py)

它做了这些增强：

- 用环境变量控制模型路径、batch size、并发数、fp16
- 使用 `healthz` 和 `readyz`
- 不向客户端回传 traceback
- 默认限制单容器并发 encode 数
- 更适合离线镜像运行

## 目录里的文件

- [embedding_service_prod.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/embedding_service_prod.py)：生产版服务
- [requirements-service.txt](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/requirements-service.txt)：镜像最小依赖
- [download_bge_m3.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/download_bge_m3.py)：构建时下载模型
- [Dockerfile.bge-m3](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/Dockerfile.bge-m3)：镜像构建文件
- [run_bge_m3_multi_gpu.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_multi_gpu.sh)：多 GPU 启动脚本
- [docker-runtime.env](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/docker-runtime.env)：运行时配置文件
- [docker-compose.bge-m3.yml](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/docker-compose.bge-m3.yml)：compose 示例

## 一、构建环境准备

构建环境需要：

- Docker
- 能访问 Hugging Face 模型仓库
- 如果要在构建机上顺手验证 GPU 版运行，构建机还需要 NVIDIA 驱动和 `nvidia-container-toolkit`

## 二、在联网构建环境构建镜像

在仓库根目录执行：

```bash
docker build -f 04_vectorDB/02_hybrid_search/embedding_service/Dockerfile.bge-m3 -t rag-in-one/bge-m3-embed:latest .
```

这个过程会：

- 安装运行时依赖
- 下载 `BAAI/bge-m3` 到镜像内的 `/models/BAAI_bge-m3`
- 把服务代码打进去

构建完成后，可以先在联网环境本地验证镜像：

如果构建机本身有 GPU，并且想验证 GPU 运行：

```bash
docker run --rm --gpus all -p 18080:18080 rag-in-one/bge-m3-embed:latest
```

如果构建机没有 GPU，只想验证服务能否启动：

```bash
docker run --rm -e EMBEDDING_DEVICE=cpu -p 18080:18080 rag-in-one/bge-m3-embed:latest
```

## 三、导出镜像

```bash
docker save -o bge-m3-embed-latest.tar rag-in-one/bge-m3-embed:latest
```

把这个 tar 包拷贝到生产环境。

## 四、生产环境准备

生产环境需要：

- Docker
- NVIDIA 驱动
- `nvidia-container-toolkit`

先确认宿主机自己能看到 GPU：

```bash
nvidia-smi
```

如果这一步不通，先不要起 embedding 服务，先把宿主机 GPU 驱动问题处理好。

再确认 Docker 的 GPU 透传是通的。

如果生产环境已经导入了 embedding 业务镜像，推荐直接用这个镜像验证：

```bash
docker run --rm --gpus all rag-in-one/bge-m3-embed:latest python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"
```

这一步不依赖额外在线拉取 `nvidia/cuda` 测试镜像，更适合无法联网的生产环境。

如果你们希望保留 `nvidia/cuda` 这种独立测试方式，也可以在公网构建环境提前把测试镜像一起导出，再在生产环境 `docker load` 后使用。

如果上面这一步仍然不方便，最直接的验证方式就是：

1. 先按本文后面的步骤启动 embedding 容器
2. 再在宿主机执行 `nvidia-smi`
3. 确认 GPU 已被对应容器进程占用

## 五、在生产环境导入镜像

```bash
docker load -i bge-m3-embed-latest.tar
```

## 六、按配置文件启动服务

### 推荐方式：按 GPU 数量起容器，每张卡 1 个实例

先编辑运行时配置文件：

```bash
vi /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/docker-runtime.env
```

默认配置是：

```bash
GPU_DEVICES=all
HOST_PORT_BASE=18080
CONTAINER_PREFIX=bge_m3
```

含义是：

- `GPU_DEVICES=all`：自动发现宿主机上所有 GPU，并每张卡启动一个容器
- `HOST_PORT_BASE=18080`：第一个容器用 `18080`，第二个用 `18081`，依次递增
- `CONTAINER_PREFIX=bge_m3`：容器名会生成为 `bge_m3_gpu0`、`bge_m3_gpu1` 这种格式

如果你只想用部分卡，例如只用 `0,1`：

```bash
GPU_DEVICES=0,1
```

如果将来机器扩成更多卡，而你希望默认全部用上，就继续保持：

```bash
GPU_DEVICES=all
```

再给脚本执行权限：

```bash
chmod +x /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_multi_gpu.sh
```

执行：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_multi_gpu.sh
```

例如在 2 张卡的机器上，默认会启动：

- `bge_m3_gpu0` -> `18080`
- `bge_m3_gpu1` -> `18081`

注意：

- 脚本会为每张 GPU 启动一个独立容器，而不是让一个 Python 进程直接管理所有 GPU
- 这是因为当前 `bge-m3` 服务实现更适合“一卡一实例”，这样更稳，也更容易扩缩容
- 容器内统一使用 `EMBEDDING_DEVICE=cuda:0`
- 这是因为每个容器只看得到自己绑定的那一张物理卡
- GPU 隔离由 Docker 的 `--gpus device=...` 完成，不再额外手动设置 `CUDA_VISIBLE_DEVICES`，避免二次过滤后把 GPU 隐藏掉

## 七、健康检查与功能检查

检查实例是否 ready：

```bash
curl http://127.0.0.1:18080/readyz
curl http://127.0.0.1:18081/readyz
```

测试 dense：

```bash
curl -X POST http://127.0.0.1:18080/embed/dense \
  -H 'Content-Type: application/json' \
  -d '{"texts":["你好，帮我生成一个向量"]}'
```

测试 sparse：

```bash
curl -X POST http://127.0.0.1:18081/embed/sparse \
  -H 'Content-Type: application/json' \
  -d '{"texts":["混合检索测试文本"]}'
```

查看 GPU 使用情况：

```bash
nvidia-smi
```

查看容器日志：

```bash
docker logs -f bge_m3_gpu0
docker logs -f bge_m3_gpu1
```

## 八、生产参数建议

针对 T4，建议先从下面这组参数开始压测：

- `EMBEDDING_USE_FP16=true`
- `EMBEDDING_BATCH_SIZE=16` 或 `32`
- `EMBEDDING_MAX_CONCURRENT_REQUESTS=1`

建议先保守一点，确认稳定后再逐步提高：

1. 先固定 `MAX_CONCURRENT_REQUESTS=1`
2. 再逐步把 `BATCH_SIZE` 从 `16` 提到 `32`
3. 如果显存还有余量，再评估是否提高输入上限

## 九、如何对外提供统一入口

最简单的方式有两种：

1. 调用方自己做轮询
2. 前面再加一个轻量代理层

如果你们现有生产环境已经有 Nginx、HAProxy 或 API Gateway，推荐把：

- `18080`
- `18081`

作为两个后端做轮询转发。

这样 embedding 服务本身保持简单，扩容和摘流量也更容易。

如果你们准备用 Nginx，可以直接参考：

- [nginx.embedding.conf](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/nginx.embedding.conf)

这个配置默认把：

- `127.0.0.1:18080`
- `127.0.0.1:18081`

作为 upstream 后端，并通过 `8080` 对外提供统一入口。

## 十、回滚方式

如果新镜像有问题，回滚最简单：

1. 停掉两个容器
2. `docker load` 旧版本 tar
3. 用旧镜像 tag 重新起两个容器

## 十一、建议的生产结论

对你这个场景，推荐的最终形态是：

- 继续保留当前 [embedding_service.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/embedding_service.py) 作为开发验证版
- 生产环境使用 [embedding_service_prod.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/embedding_service_prod.py)
- 通过 [docker-runtime.env](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/docker-runtime.env) 指定 `GPU_DEVICES=all` 或具体卡号
- 每张 GPU 跑一个容器实例
- 构建时把模型直接烘焙进镜像
- 生产环境只做离线导入和运行

这比“一个服务进程同时管理两张 GPU”更稳，也更符合生产环境的可控性要求。

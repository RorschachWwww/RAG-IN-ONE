# BGE-M3 离线生产部署方案

这个方案面向如下场景：

- 构建环境可以联网
- 生产环境不能联网
- 生产环境有 2 张 NVIDIA T4 GPU
- 希望把 `bge-m3` 做成长期运行的 embedding 服务

## 总体方案

推荐方案是：

1. 在联网的构建环境里构建 Docker 镜像
2. 构建时把 `BAAI/bge-m3` 模型权重直接下载进镜像
3. 把镜像 `docker save` 成 tar 包
4. 把 tar 包拷贝到生产环境
5. 在生产环境 `docker load`
6. 分别起 2 个容器，每个容器绑定 1 张 GPU

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
- [run_bge_m3_dual_gpu.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_dual_gpu.sh)：双 GPU 启动脚本
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

```bash
docker run --rm -p 18080:18080 rag-in-one/bge-m3-embed:latest
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

先确认 Docker 能看到 GPU：

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

如果这一步不通，先不要起 embedding 服务，先把容器 GPU 运行环境打通。

## 五、在生产环境导入镜像

```bash
docker load -i bge-m3-embed-latest.tar
```

## 六、在 2 张 T4 上启动服务

### 推荐方式：起 2 个容器，每张卡 1 个实例

先给脚本执行权限：

```bash
chmod +x /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_dual_gpu.sh
```

执行：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_dual_gpu.sh
```

启动后端口对应关系：

- `18080` -> GPU 0 实例
- `18081` -> GPU 1 实例

### 等价的手工启动命令

GPU 0：

```bash
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
  rag-in-one/bge-m3-embed:latest
```

GPU 1：

```bash
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
  rag-in-one/bge-m3-embed:latest
```

注意：

- 第二个容器里虽然写的是 `EMBEDDING_DEVICE=cuda:0`，但这是对容器内部来说的
- 因为它只看得到 `CUDA_VISIBLE_DEVICES=1` 暴露进来的那一张物理卡
- 所以容器内的 `cuda:0` 实际对应宿主机的物理 `GPU 1`

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

## 十、回滚方式

如果新镜像有问题，回滚最简单：

1. 停掉两个容器
2. `docker load` 旧版本 tar
3. 用旧镜像 tag 重新起两个容器

## 十一、建议的生产结论

对你这个场景，推荐的最终形态是：

- 继续保留当前 [embedding_service.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/embedding_service.py) 作为开发验证版
- 生产环境使用 [embedding_service_prod.py](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/embedding_service_prod.py)
- 一张 T4 跑一个容器实例
- 构建时把模型直接烘焙进镜像
- 生产环境只做离线导入和运行

这比“一个服务进程同时管理两张 GPU”更稳，也更符合生产环境的可控性要求。

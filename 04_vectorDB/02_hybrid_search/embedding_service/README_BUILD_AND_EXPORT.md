# 构建环境运行与镜像导出

这份说明只覆盖两件事：

1. 在公网构建环境先把 `bge-m3` 容器跑起来做验证
2. 把已经构建好的 image 导出成文件，拷贝到无法联网的生产环境

相关脚本：

- [run_bge_m3_build_env.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_build_env.sh)
- [export_bge_m3_image.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/export_bge_m3_image.sh)

## 1. 在构建环境启动容器

默认使用：

- image: `rag-in-one/bge-m3-embed:latest`
- 容器名: `bge_m3_build_env`
- 宿主机端口: `18080`
- GPU: `0`

执行：

```bash
chmod +x /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_build_env.sh
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_build_env.sh
```

如果目标环境本地还没有这个 image，但你手头有导出的 tar 文件，也可以让脚本先自动导入再启动：

```bash
IMAGE_TAR=/path/to/bge-m3-embed-latest.tar \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_build_env.sh
```

如果你要在生产环境按“所有 GPU 默认全用上”的方式启动，不要用这个单实例脚本，直接看
[README_PROD.md](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/README_PROD.md)
里的 `run_bge_m3_multi_gpu.sh` 和 `docker-runtime.env`。

如果你想改端口或 GPU，可以这样：

```bash
HOST_PORT=18081 GPU_DEVICE=1 CONTAINER_NAME=bge_m3_build_env_gpu1 \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_build_env.sh
```

启动后可以检查：

```bash
curl http://127.0.0.1:18080/healthz
curl http://127.0.0.1:18080/readyz
docker logs -f bge_m3_build_env
nvidia-smi
```

测试 dense 接口：

```bash
curl -X POST http://127.0.0.1:18080/embed/dense \
  -H 'Content-Type: application/json' \
  -d '{"texts":["你好，帮我生成一个向量"]}'
```

停止并删除容器：

```bash
docker rm -f bge_m3_build_env
```

## 2. 导出 image 成文件

执行：

```bash
chmod +x /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/export_bge_m3_image.sh
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/export_bge_m3_image.sh
```

默认会把镜像导出到当前目录下的 `dist/bge-m3-embed-latest.tar`。

如果你想改输出目录或文件名：

```bash
OUTPUT_DIR=/tmp OUTPUT_FILE=bge-m3-prod-20260529.tar \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/export_bge_m3_image.sh
```

如果你想导出别的镜像 tag：

```bash
IMAGE_NAME=rag-in-one/bge-m3-embed:v1.0.0 \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/export_bge_m3_image.sh
```

## 3. 导入到生产环境

把 tar 文件拷贝到生产环境后，执行：

```bash
docker load -i bge-m3-embed-latest.tar
```

导入完成后，再按 [README_PROD.md](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/README_PROD.md) 里的生产方式启动容器。

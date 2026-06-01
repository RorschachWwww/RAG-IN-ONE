# Embedding Service 打包清单

如果你要把 embedding 服务从构建环境带到生产环境，生产运行最少需要这些文件：

- [run_bge_m3_multi_gpu.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/run_bge_m3_multi_gpu.sh)
- [docker-runtime.env](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/docker-runtime.env)
- [README_PROD.md](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/README_PROD.md)
- [nginx.embedding.conf](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/nginx.embedding.conf)
- [download_nvidia_container_toolkit_offline.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/download_nvidia_container_toolkit_offline.sh)
- [install_nvidia_container_toolkit_offline.sh](/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/install_nvidia_container_toolkit_offline.sh)

如果你还没有把 image 导入到生产环境，还需要镜像 tar 文件，例如：

- `bge-m3-embed-latest.tar`

如果生产环境无法联网安装 NVIDIA Container Toolkit，可以在同系统版本的联网机器上执行：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/download_nvidia_container_toolkit_offline.sh
```

然后把生成的 `nvidia-container-toolkit-offline` 目录拷到生产环境，执行：

```bash
sudo bash install_nvidia_container_toolkit_offline.sh --bundle-dir /path/to/nvidia-container-toolkit-offline
```

## 一键收集脚本

可以直接执行：

```bash
chmod +x /Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh
```

默认行为：

- 固定拷贝生产运行必需文件
- 在“当前执行目录”查找 `bge-m3-embed*.tar`
- 如果找到了，就一起拷贝进 bundle 目录
- 如果当前目录没有 tar 包，就自动跳过，不报错

默认输出目录：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/bundle_embedding_service
```

## 可选参数

如果你想用传参方式改输出目录：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh \
  --bundle-dir /tmp/embedding_bundle
```

如果你想同时指定 tar 查找目录：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh \
  --bundle-dir /tmp/embedding_bundle \
  --search-dir /path/to/tar/files
```

如果你想改 tar 匹配规则：

```bash
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh \
  --bundle-dir /tmp/embedding_bundle \
  --tar-glob '*.tar'
```

如果你还是想用环境变量方式，也仍然支持。

如果你想改输出目录：

```bash
BUNDLE_DIR=/tmp/embedding_bundle \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh
```

如果你想指定 tar 查找目录：

```bash
SEARCH_DIR=/path/to/tar/files \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh
```

如果你想改 tar 匹配规则：

```bash
TAR_GLOB='*.tar' \
/Users/wuxucan/code/rag-codes/RAG-IN-ONE/04_vectorDB/02_hybrid_search/embedding_service/collect_embedding_service_bundle.sh
```

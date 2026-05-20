# embedding_service

这个目录只放 `bge-m3` embedding 服务相关文件。混合检索脚本仍然保留在上一级 `02_hybrid_search` 目录。

## 启动 embedding 服务

进入当前目录后启动服务：

```bash
uvicorn embedding_service:app --host 0.0.0.0 --port 18080
```

## 指定某个 GPU 运行 embedding 模型

`embedding_service.py` 现在支持两种方式固定 GPU。

### 方式 1：直接指定设备

把模型直接放到某张卡上，例如 GPU 1：

```bash
EMBEDDING_DEVICE=cuda:1 uvicorn embedding_service:app --host 0.0.0.0 --port 18080
```

现在如果你传的是 `EMBEDDING_DEVICE=cuda:N`，服务也会自动把当前进程的
`CUDA_VISIBLE_DEVICES` 收敛到这张卡，避免多 GPU 环境里其他卡也被初始化。

常见写法：

```bash
EMBEDDING_DEVICE=cuda:0 uvicorn embedding_service:app --host 0.0.0.0 --port 18080
EMBEDDING_DEVICE=cuda:1 uvicorn embedding_service:app --host 0.0.0.0 --port 18080
```

### 方式 2：限制进程只看到某张 GPU

如果你希望这个服务进程不要占用环境里的所有 GPU，推荐这种方式：

```bash
EMBEDDING_CUDA_DEVICE=1 uvicorn embedding_service:app --host 0.0.0.0 --port 18080
```

这会在服务启动时自动设置：

```bash
CUDA_VISIBLE_DEVICES=1
```

此时进程通常只会看到这一张卡，更适合多 GPU 环境。

## 查看是否生效

### 1. 看健康检查

```bash
curl http://127.0.0.1:18080/health
```

返回里重点看这几个字段：

- `device`
- `resolved_device`
- `cuda_visible_devices`

例如：

```json
{
  "ok": true,
  "model_loaded": true,
  "model_id": "BAAI/bge-m3",
  "device": "cuda:1",
  "resolved_device": "cuda:0",
  "cuda_visible_devices": "1"
}
```

或者：

```json
{
  "ok": true,
  "model_loaded": true,
  "model_id": "BAAI/bge-m3",
  "device": "auto",
  "resolved_device": "cuda",
  "cuda_visible_devices": "1"
}
```

### 2. 看启动日志

启动时通常会打印类似日志：

```text
[startup] Model loaded: BAAI/bge-m3 device=cuda:1 fp16=False cost=...
```

### 3. 看 GPU 进程

```bash
nvidia-smi
```

或者：

```bash
nvidia-smi pmon -c 1
```

## 测试接口是否正常

### health

```bash
curl http://127.0.0.1:18080/health
```

### dense embedding

```bash
curl -X POST http://127.0.0.1:18080/embed/dense \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["你好，帮我生成一个向量"]
  }'
```

### sparse embedding

```bash
curl -X POST http://127.0.0.1:18080/embed/sparse \
  -H 'Content-Type: application/json' \
  -d '{
    "texts": ["混合检索测试文本"]
  }'
```

### both

```bash
curl -X POST http://127.0.0.1:18080/embed/both \
  -H 'Content-Type: application/json' \
  -d '{
    "dense_texts": ["这是 dense 输入"],
    "sparse_texts": ["这是 sparse 输入"]
  }'
```

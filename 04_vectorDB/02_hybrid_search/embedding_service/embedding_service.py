import os
import time
import traceback
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# =========================================================
# 配置区（你可以按需修改，但这里保持“写死”方便 demo）
# =========================================================
MODEL_ID = "BAAI/bge-m3"

# 设备选择：
# - "auto"：自动选择 cuda / mps / cpu（按可用性）
# - "mps"：Mac Apple Silicon 的 GPU 后端（速度快，但有时兼容性略差）
# - "cpu"：最稳，但最慢
# - "cuda" / "cuda:1"：NVIDIA GPU
# 也支持通过环境变量 EMBEDDING_DEVICE 覆盖，例如：
#   EMBEDDING_DEVICE=cuda:1
DEVICE = os.getenv("EMBEDDING_DEVICE", "auto").strip().lower()

# 如果你更习惯传 GPU 编号，可以设置 EMBEDDING_CUDA_DEVICE。
# 这会在导入 torch 前收敛可见卡，避免一个进程把所有 GPU 都暴露出来。
# 例如：
#   EMBEDDING_CUDA_DEVICE=1
CUDA_DEVICE = os.getenv("EMBEDDING_CUDA_DEVICE", "").strip()


def _extract_cuda_index(device: str) -> str:
    """
    从 "cuda:N" 中提取 N；如果不是这种格式，则返回空字符串。
    """
    if not device.startswith("cuda:"):
        return ""
    _, _, idx = device.partition(":")
    return idx if idx.isdigit() else ""


# 如果用户显式传了 EMBEDDING_DEVICE=cuda:N，但没传 EMBEDDING_CUDA_DEVICE，
# 默认也把可见卡收敛到 N，避免多卡环境里其他 GPU 也被当前进程初始化。
if not CUDA_DEVICE:
    CUDA_DEVICE = _extract_cuda_index(DEVICE)

if CUDA_DEVICE and "CUDA_VISIBLE_DEVICES" not in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = CUDA_DEVICE

# 是否使用 FP16：
# - Mac 上 mps + fp16 可能在某些组合下不稳定，所以默认 False
USE_FP16 = False

# 服务端做 embedding 时的 batch size（单次 encode 处理多少条文本）
BATCH_SIZE = 32

# FastAPI 应用实例
app = FastAPI(title="Embedding Service (BGE-M3 via FlagEmbedding)")

# 全局模型对象（服务启动时加载一次，之后复用）
_model = None
_resolved_device = None


# =========================================================
# 工具函数：设备选择 / 结果兼容 / sparse 格式转换
# =========================================================
def resolve_device(device: str) -> str:
    """
    将 DEVICE="auto" 解析为实际设备：
    - 如果有 CUDA：cuda
    - 否则如果有 MPS（Mac）：mps
    - 否则：cpu

    如果你显式传 cpu/cuda/mps/cuda:N，也会直接返回。

    额外说明：
    - 如果已经设置了 CUDA_VISIBLE_DEVICES，那么当前进程里可见 GPU 会被重编号。
      例如物理卡 1 在进程内会表现为 cuda:0。
    """
    device = (device or "auto").lower()
    if device in ("cpu", "cuda", "mps"):
        return device
    if device.startswith("cuda:"):
        if os.getenv("CUDA_VISIBLE_DEVICES"):
            return "cuda:0"
        return device

    # auto：动态判断 torch 的可用后端
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def pick_dense_vecs(out: Dict[str, Any]):
    """
    从 FlagEmbedding 的 encode 输出中取出 dense 向量矩阵。

    ✅ 为什么要写这个函数？
    不同 FlagEmbedding 版本 encode() 的返回字段名不完全一致：
    - 有的叫 "dense_vecs"
    - 有的叫 "dense"
    - 极少数版本可能叫 "embeddings"

    ⚠️ 关键点：这里不能用 `out.get("dense_vecs") or out.get("dense")`
    因为 out.get(...) 返回的是 numpy array，numpy array 不能直接做 bool 判断，
    否则会出现你之前遇到的：
    ValueError: The truth value of an array with more than one element is ambiguous
    """
    vecs = out.get("dense_vecs", None)
    if vecs is None:
        vecs = out.get("dense", None)
    if vecs is None:
        vecs = out.get("embeddings", None)
    if vecs is None:
        # 兜底：直接把 keys 打出来方便排查版本差异
        raise RuntimeError(f"Unexpected dense output keys: {list(out.keys())}")
    return vecs


def pick_sparse_list(out: Dict[str, Any]) -> List[Any]:
    """
    从 FlagEmbedding 的 encode 输出中取出 sparse 向量列表。

    ✅ 为什么要兼容多个 key？
    FlagEmbedding / BGE-M3 的 sparse 输出字段，在不同版本可能叫：
    - "sparse"
    - "sparse_vecs"
    - "sparse_embeddings"
    - "lexical_weights"

    返回结果通常是一个 list，list 中每个元素对应一条文本的 sparse 表示。
    """
    for k in ("sparse", "sparse_vecs", "sparse_embeddings", "lexical_weights"):
        if k in out:
            return out[k]
    raise KeyError(f"No sparse field found. keys={list(out.keys())}")


def sparse_to_dict(obj: Any) -> Dict[int, float]:
    """
    将 FlagEmbedding 输出的 sparse 结构，转换为 Milvus 所需要的 SPARSE_FLOAT_VECTOR 格式：
      dict[int, float]  （稀疏向量 = {维度索引: 权重}）

    ✅ 支持的输入格式（不同版本/实现可能不同）：
    1）{"indices":[...], "values":[...]}
    2）[{"index":..,"value":..}, ...]
    3）{int_key: weight, ...}  （key 必须能转为 int）

    ⚠️ 注意：Milvus 的 sparse 向量必须是 “int -> float”
    如果 sparse 输出的 key 是 token 字符串（如 "管理员" -> 0.123），
    则无法直接写入 Milvus，需要额外用 tokenizer 把 token 映射到 token_id。
    这里做的是“最常见可写入格式”的转换。
    """
    # 形式 1：indices + values
    if isinstance(obj, dict) and "indices" in obj and "values" in obj:
        return {int(i): float(v) for i, v in zip(obj["indices"], obj["values"])}

    # 形式 2：list of {"index","value"}
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "index" in obj[0] and "value" in obj[0]:
        return {int(p["index"]): float(p["value"]) for p in obj}

    # 形式 3：dict-like，尝试把 key 转 int
    if isinstance(obj, dict):
        out: Dict[int, float] = {}
        for k, v in obj.items():
            try:
                out[int(k)] = float(v)
            except Exception:
                # 如果 key 不是 int（例如 token 字符串），这里会跳过
                pass
        if out:
            return out

    # 兜底：格式不在以上三种情况内，直接抛错并带 sample
    raise TypeError(f"Unsupported sparse format: type={type(obj)} sample={str(obj)[:200]}")


# =========================================================
# 启动钩子：服务启动时只加载一次模型（关键：避免每次脚本运行都加载）
# =========================================================
@app.on_event("startup")
def startup():
    """
    FastAPI/uvicorn 启动时自动执行。
    我们在这里加载 BGEM3FlagModel，并保存在全局 _model 中。

    ✅ 好处：
    - 模型只加载一次（2GB+），后续请求直接复用
    - ingest/search 脚本不需要再加载模型，只需要 HTTP 调用服务
    """
    global _model, _resolved_device
    import torch
    from FlagEmbedding import BGEM3FlagModel

    real_device = resolve_device(DEVICE)
    _resolved_device = real_device
    if real_device.startswith("cuda"):
        torch.cuda.set_device(real_device)
    t0 = time.time()
    _model = BGEM3FlagModel(MODEL_ID, use_fp16=USE_FP16, device=real_device)
    print(f"[startup] Model loaded: {MODEL_ID} device={real_device} fp16={USE_FP16} cost={time.time()-t0:.3f}s")


# =========================================================
# 请求体（Pydantic Model）：用于 FastAPI 自动校验 JSON 入参
# =========================================================
class DenseReq(BaseModel):
    # 需要生成 dense 向量的文本列表
    texts: List[str]


class SparseReq(BaseModel):
    # 需要生成 sparse 向量的文本列表
    texts: List[str]


class BothReq(BaseModel):
    # dense 的输入文本列表
    dense_texts: List[str]
    # sparse 的输入文本列表
    sparse_texts: List[str]


# =========================================================
# 接口区：health / embed/dense / embed/sparse / embed/both
# =========================================================
@app.get("/health")
def health():
    """
    健康检查接口：用于确认服务已启动、模型已加载。
    """
    return {
        "ok": True,
        "model_loaded": _model is not None,
        "model_id": MODEL_ID,
        "device": DEVICE,
        "resolved_device": _resolved_device,
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "fp16": USE_FP16,
        "batch_size": BATCH_SIZE,
    }


@app.post("/embed/dense")
def embed_dense(req: DenseReq):
    """
    生成 dense 向量：
    输入：{"texts": ["...", "..."]}
    输出：{"dim": 1024, "vectors": [[...], [...]]}
    """
    if _model is None:
        # 模型还没加载好（理论上不会出现，除非 startup 失败）
        return JSONResponse(status_code=503, content={"error": "model not loaded"})

    try:
        t0 = time.time()

        # FlagEmbedding 的 encode：
        # - return_dense=True 表示输出 dense
        # - return_sparse=False 表示不输出 sparse
        out = _model.encode(
            req.texts,
            batch_size=min(BATCH_SIZE, len(req.texts)),
            return_dense=True,
            return_sparse=False,
        )

        # 从不同版本输出中取 dense 矩阵
        vecs = pick_dense_vecs(out)

        return {
            "cost_sec": round(time.time() - t0, 4),
            "dim": int(vecs.shape[1]),
            "vectors": vecs.tolist(),
            # keys 方便你观察当前版本到底返回了哪些字段
            "keys": list(out.keys()),
        }

    except Exception as e:
        # 把 traceback 返回给调用方（客户端），方便快速定位
        return JSONResponse(
            status_code=500,
            content={
                "error": "embed_dense failed",
                "exception": repr(e),
                "traceback": traceback.format_exc(),
            },
        )


@app.post("/embed/sparse")
def embed_sparse(req: SparseReq):
    """
    生成 learned sparse（稀疏）向量：
    输入：{"texts": ["...", "..."]}
    输出：{"vectors": [ {idx:weight, ...}, {idx:weight, ...} ]}

    ⚠️ Milvus 的 SPARSE_FLOAT_VECTOR 要求：dict[int,float]
    """
    if _model is None:
        return JSONResponse(status_code=503, content={"error": "model not loaded"})

    try:
        t0 = time.time()

        out = _model.encode(
            req.texts,
            batch_size=min(BATCH_SIZE, len(req.texts)),
            return_dense=False,
            return_sparse=True,
        )

        # 兼容不同版本的 sparse 字段名
        sparse_list = pick_sparse_list(out)

        # 理论上应该是 list（每条文本一个 sparse）
        if not isinstance(sparse_list, list):
            raise TypeError(f"Expected sparse_list list, got {type(sparse_list)} keys={list(out.keys())}")

        # 转成 Milvus 可接受的 dict[int,float]
        vectors = [sparse_to_dict(x) for x in sparse_list]

        # 快速 sanity check：如果转换后为空，说明 sparse key 很可能是 token 字符串，不是 token_id
        if vectors and len(vectors[0]) == 0:
            raise ValueError(
                "Sparse vector converted to empty dict. "
                "This often means sparse output keys are tokens (not int ids). "
                "Need tokenizer mapping token->id for Milvus sparse."
            )

        return {
            "cost_sec": round(time.time() - t0, 4),
            "vectors": vectors,
            "keys": list(out.keys()),
        }

    except Exception as e:
        # 如果 out 不存在（encode 直接抛异常），keys 就会是 None
        keys = None
        try:
            keys = list(out.keys())  # type: ignore
        except Exception:
            pass

        return JSONResponse(
            status_code=500,
            content={
                "error": "embed_sparse failed",
                "exception": repr(e),
                "keys": keys,
                "traceback": traceback.format_exc(),
            },
        )


@app.post("/embed/both")
def embed_both(req: BothReq):
    """
    同时生成 dense + sparse（减少一次网络往返）：
    输入：{"dense_texts":[...], "sparse_texts":[...]}
    输出：{"dense": {...}, "sparse": {...}}

    ✅ 适合 ingest：一批 chunks 生成 dense，同时一批 IDs 生成 sparse
    """
    if _model is None:
        return JSONResponse(status_code=503, content={"error": "model not loaded"})

    try:
        t0 = time.time()

        # ---- dense 部分
        dense_out = _model.encode(
            req.dense_texts,
            batch_size=min(BATCH_SIZE, len(req.dense_texts)),
            return_dense=True,
            return_sparse=False,
        )
        dense_vecs = pick_dense_vecs(dense_out)

        # ---- sparse 部分
        sparse_out = _model.encode(
            req.sparse_texts,
            batch_size=min(BATCH_SIZE, len(req.sparse_texts)),
            return_dense=False,
            return_sparse=True,
        )
        sparse_list = pick_sparse_list(sparse_out)

        if not isinstance(sparse_list, list):
            raise TypeError(f"Expected sparse_list list, got {type(sparse_list)} keys={list(sparse_out.keys())}")

        sparse_vecs = [sparse_to_dict(x) for x in sparse_list]

        if sparse_vecs and len(sparse_vecs[0]) == 0:
            raise ValueError(
                "Sparse vector converted to empty dict. "
                "This often means sparse output keys are tokens (not int ids). "
                "Need tokenizer mapping token->id for Milvus sparse."
            )

        return {
            "cost_sec": round(time.time() - t0, 4),
            "dense": {
                "dim": int(dense_vecs.shape[1]),
                "vectors": dense_vecs.tolist(),
                "keys": list(dense_out.keys()),
            },
            "sparse": {
                "vectors": sparse_vecs,
                "keys": list(sparse_out.keys()),
            },
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "embed_both failed",
                "exception": repr(e),
                "traceback": traceback.format_exc(),
            },
        )

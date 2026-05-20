import logging
import os
import time
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "/models/BAAI_bge-m3")
DEVICE = os.getenv("EMBEDDING_DEVICE", "cuda")
USE_FP16 = _env_bool("EMBEDDING_USE_FP16", True)
BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
MAX_TEXTS = int(os.getenv("EMBEDDING_MAX_TEXTS", "128"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("EMBEDDING_MAX_CONCURRENT_REQUESTS", "1"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("embedding_service_prod")

app_state: Dict[str, Any] = {
    "model": None,
    "resolved_device": None,
    "started_at": None,
}
encode_slots = BoundedSemaphore(value=MAX_CONCURRENT_REQUESTS)


def resolve_device(device: str) -> str:
    device = (device or "auto").strip().lower()
    if device in ("cpu", "cuda", "mps"):
        return device
    if device.startswith("cuda:"):
        return device

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        logger.exception("Resolve device failed, fallback to cpu")
    return "cpu"


def pick_dense_vecs(out: Dict[str, Any]):
    vecs = out.get("dense_vecs")
    if vecs is None:
        vecs = out.get("dense")
    if vecs is None:
        vecs = out.get("embeddings")
    if vecs is None:
        raise RuntimeError(f"Unexpected dense output keys: {list(out.keys())}")
    return vecs


def pick_sparse_list(out: Dict[str, Any]) -> List[Any]:
    for key in ("sparse", "sparse_vecs", "sparse_embeddings", "lexical_weights"):
        if key in out:
            return out[key]
    raise RuntimeError(f"Unexpected sparse output keys: {list(out.keys())}")


def sparse_to_dict(obj: Any) -> Dict[int, float]:
    if isinstance(obj, dict) and "indices" in obj and "values" in obj:
        return {int(i): float(v) for i, v in zip(obj["indices"], obj["values"])}

    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "index" in obj[0] and "value" in obj[0]:
        return {int(item["index"]): float(item["value"]) for item in obj}

    if isinstance(obj, dict):
        out: Dict[int, float] = {}
        for k, v in obj.items():
            try:
                out[int(k)] = float(v)
            except Exception:
                continue
        if out:
            return out

    raise TypeError(f"Unsupported sparse format: type={type(obj)}")


def _validate_texts(texts: List[str]):
    if not texts:
        raise HTTPException(status_code=400, detail="texts must not be empty")
    if len(texts) > MAX_TEXTS:
        raise HTTPException(status_code=400, detail=f"text count exceeds limit: {MAX_TEXTS}")


def _encode_guard():
    acquired = encode_slots.acquire(timeout=600)
    if not acquired:
        raise HTTPException(status_code=503, detail="service busy")
    return acquired


@asynccontextmanager
async def lifespan(app: FastAPI):
    import torch
    from FlagEmbedding import BGEM3FlagModel

    real_device = resolve_device(DEVICE)
    if real_device.startswith("cuda"):
        torch.cuda.set_device(real_device)

    t0 = time.time()
    model = BGEM3FlagModel(MODEL_ID, use_fp16=USE_FP16, device=real_device)
    app_state["model"] = model
    app_state["resolved_device"] = real_device
    app_state["started_at"] = time.time()
    logger.info(
        "model loaded model_id=%s resolved_device=%s fp16=%s load_cost_sec=%.3f",
        MODEL_ID,
        real_device,
        USE_FP16,
        time.time() - t0,
    )
    yield
    app_state["model"] = None


app = FastAPI(title="Embedding Service Prod (BGE-M3)", lifespan=lifespan)


class DenseReq(BaseModel):
    texts: List[str] = Field(..., min_length=1)


class SparseReq(BaseModel):
    texts: List[str] = Field(..., min_length=1)


class BothReq(BaseModel):
    dense_texts: List[str] = Field(..., min_length=1)
    sparse_texts: List[str] = Field(..., min_length=1)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    return {
        "ok": app_state["model"] is not None,
        "model_id": MODEL_ID,
        "resolved_device": app_state["resolved_device"],
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "batch_size": BATCH_SIZE,
        "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
    }


@app.post("/embed/dense")
def embed_dense(req: DenseReq):
    _validate_texts(req.texts)
    model = app_state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    t0 = time.time()
    _encode_guard()
    try:
        out = model.encode(
            req.texts,
            batch_size=min(BATCH_SIZE, len(req.texts)),
            return_dense=True,
            return_sparse=False,
        )
    except Exception:
        logger.exception("dense encode failed")
        raise HTTPException(status_code=500, detail="embed_dense failed")
    finally:
        encode_slots.release()

    vecs = pick_dense_vecs(out)
    return {
        "cost_sec": round(time.time() - t0, 4),
        "dim": int(vecs.shape[1]),
        "vectors": vecs.tolist(),
    }


@app.post("/embed/sparse")
def embed_sparse(req: SparseReq):
    _validate_texts(req.texts)
    model = app_state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    t0 = time.time()
    _encode_guard()
    try:
        out = model.encode(
            req.texts,
            batch_size=min(BATCH_SIZE, len(req.texts)),
            return_dense=False,
            return_sparse=True,
        )
    except Exception:
        logger.exception("sparse encode failed")
        raise HTTPException(status_code=500, detail="embed_sparse failed")
    finally:
        encode_slots.release()

    sparse_list = pick_sparse_list(out)
    return {
        "cost_sec": round(time.time() - t0, 4),
        "vectors": [sparse_to_dict(item) for item in sparse_list],
    }


@app.post("/embed/both")
def embed_both(req: BothReq):
    _validate_texts(req.dense_texts)
    _validate_texts(req.sparse_texts)
    model = app_state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    t0 = time.time()
    _encode_guard()
    try:
        dense_out = model.encode(
            req.dense_texts,
            batch_size=min(BATCH_SIZE, len(req.dense_texts)),
            return_dense=True,
            return_sparse=False,
        )
        sparse_out = model.encode(
            req.sparse_texts,
            batch_size=min(BATCH_SIZE, len(req.sparse_texts)),
            return_dense=False,
            return_sparse=True,
        )
    except Exception:
        logger.exception("both encode failed")
        raise HTTPException(status_code=500, detail="embed_both failed")
    finally:
        encode_slots.release()

    dense_vecs = pick_dense_vecs(dense_out)
    sparse_list = pick_sparse_list(sparse_out)
    return {
        "cost_sec": round(time.time() - t0, 4),
        "dense": {
            "dim": int(dense_vecs.shape[1]),
            "vectors": dense_vecs.tolist(),
        },
        "sparse": {
            "vectors": [sparse_to_dict(item) for item in sparse_list],
        },
    }

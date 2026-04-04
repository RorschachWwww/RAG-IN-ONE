import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# =========================================================
# Hardcoded Config
# =========================================================
MILVUS_URI = "http://localhost:19530"
COLLECTION_NAME = "question_hybrid_demo"
OVERWRITE_COLLECTION = True  # ingest 时是否 drop+recreate

TOPK = 3
HNSW_EF = 64

HYBRID_DENSE_WEIGHT = 0.3
HYBRID_SPARSE_WEIGHT = 0.7

# Embedding service
EMBED_BASE_URL = "http://localhost:18080"
EMBED_TIMEOUT_SEC = 120


# =========================================================
# Logging
# =========================================================
def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# =========================================================
# Paths
# common.py is under: 04_vectorDB/02_hybrid_search/common.py
# project root is: this_file.parents[2]
# CSV is: <root>/documents/others/question_export.csv
# =========================================================
def get_project_root() -> Path:
    this_file = Path(__file__).resolve()
    return this_file.parents[2]


def get_csv_path() -> Path:
    root = get_project_root()
    return root / "documents" / "others" / "question_export.csv"


# =========================================================
# Data helpers
# =========================================================
def safe_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()


def build_chunk(row: Dict[str, Any]) -> str:
    """
    每行=一个 chunk，信息密度尽可能高的“类 JSON”扁平文本。
    """
    return (
        f"id:{safe_str(row.get('ID'))}, "
        f"问题单描述:{safe_str(row.get('问题单描述'))}, "
        f"问题单生成原因:{safe_str(row.get('问题单生成原因'))}, "
        f"问题单解决方案:{safe_str(row.get('问题单解决方案'))}, "
        f"提单人:{safe_str(row.get('提单人'))}, "
        f"修改人:{safe_str(row.get('修改人'))}"
    )


def extract_ticket_id(text: str) -> Optional[str]:
    """
    从 query 中抽取“问题单号/ID”。
    支持：问题单号 12345 / 问题单ID:12345 / ID=ABC-123
    """
    m = re.search(r"(?:问题单号|问题单ID|ID)\s*[:=]?\s*([A-Za-z0-9_-]+)", text, re.IGNORECASE)
    if m:
        return m.group(1)
    m2 = re.search(r"\b(\d{4,})\b", text)
    return m2.group(1) if m2 else None


def read_csv_rows(csv_path: Path, log: logging.Logger) -> List[Dict[str, Any]]:
    """
    CSV 不存在：直接报错并退出程序（满足你的要求）
    """
    if not csv_path.exists():
        log.error(f"CSV not found: {csv_path}")
        raise FileNotFoundError(f"CSV 不存在：{csv_path}")

    log.info(f"Loading CSV: {csv_path}")
    try:
        df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, dtype=str, encoding="gbk")

    required = ["ID", "问题单描述", "问题单生成原因", "问题单解决方案", "提单人", "修改人"]
    for c in required:
        if c not in df.columns:
            log.error(f"CSV missing column: {c}. got={list(df.columns)}")
            sys.exit(1)

    rows = df.to_dict(orient="records")
    log.info(f"CSV loaded rows={len(rows)} cols={list(df.columns)}")
    return rows


# =========================================================
# Milvus field names
# =========================================================
@dataclass
class FieldNames:
    pk: str = "pk"
    text: str = "chunk"
    dense: str = "dense_vec"
    sparse: str = "sparse_vec"

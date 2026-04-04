import pwd
from typing import Dict, List
import requests


class EmbeddingClient:
    def __init__(self, base_url: str = "http://localhost:18080", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def dense(self, texts: List[str]) -> List[List[float]]:
        r = requests.post(
            f"{self.base_url}/embed/dense",
            json={"texts": texts},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["vectors"]

    def sparse(self, texts: List[str]) -> List[Dict[int, float]]:
        r = requests.post(
            f"{self.base_url}/embed/sparse",
            json={"texts": texts},
            timeout=self.timeout,
        )
        r.raise_for_status()
        # JSON object keys are strings; convert to int here
        vecs = r.json()["vectors"]
        out = []
        for d in vecs:
            out.append({int(k): float(v) for k, v in d.items()})
        return out

    def both(self, dense_texts: List[str], sparse_texts: List[str]):
        r = requests.post(
            f"{self.base_url}/embed/both",
            json={"dense_texts": dense_texts, "sparse_texts": sparse_texts},
            timeout=self.timeout,
        )
        r.raise_for_status()
        obj = r.json()
        dense_vecs = obj["dense"]["vectors"]
        sparse_vecs = []
        for d in obj["sparse"]["vectors"]:
            sparse_vecs.append({int(k): float(v) for k, v in d.items()})
        return dense_vecs, sparse_vecs

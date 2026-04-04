import argparse
import sys
import time
from typing import Optional

from pymilvus import AnnSearchRequest, MilvusClient

import common as C
from embed_client import EmbeddingClient

# 初始化日志器：统一打印检索流程日志，方便排查
log = C.setup_logger("search")


def _build_weighted_ranker(dense_w: float, bm25_w: float):
    """
    创建 Milvus Hybrid Search 使用的 WeightedRanker（加权融合重排器）。

    参数说明：
    - dense_w: dense（稠密向量）检索结果的权重
    - bm25_w : BM25（全文检索稀疏向量）检索结果的权重

    作用：
    - hybrid_search 会同时跑两路检索（dense + bm25）
    - WeightedRanker 按权重把两路结果融合成最终排序
    """
    try:
        from pymilvus import WeightedRanker
        return WeightedRanker(dense_w, bm25_w)
    except Exception:
        try:
            # 某些 pymilvus 版本 WeightedRanker 在这个路径
            from pymilvus.client.abstract import WeightedRanker  # type: ignore
            return WeightedRanker(dense_w, bm25_w)
        except Exception as e:
            raise RuntimeError(
                "Cannot import WeightedRanker. Please upgrade pymilvus: pip install -U pymilvus"
            ) from e


def dense_search(client: MilvusClient, ec: EmbeddingClient, query: str, fields: C.FieldNames, k: int):
    """
    纯 dense 检索（只走语义向量）。

    适用场景：
    - “xxx 问题怎么解决？”这种自然语言问题
    - 不依赖问题单号/关键词精确匹配

    关键参数：
    - anns_field=fields.dense：在 dense 向量字段上做 ANN 搜索
    - limit=k：返回 top-k
    - search_params={"params":{"ef": C.HNSW_EF}}：HNSW 搜索参数
        ef 越大：召回更好（更准）但更慢
        ef 越小：更快但可能漏召回
    """
    log.info(f"[Dense Search] query={query}")

    # 1) 调 embedding_service 得到 query 的 dense 向量（这里不会加载模型，只是 HTTP 请求）
    qv = ec.dense([query])[0]

    # 2) 调 Milvus search（在 dense 字段上）
    t0 = time.time()
    res = client.search(
        collection_name=C.COLLECTION_NAME,
        data=[qv],
        anns_field=fields.dense,
        limit=k,
        output_fields=[fields.pk, fields.text],
        search_params={"params": {"ef": C.HNSW_EF}},
    )
    cost = time.time() - t0

    # 3) 打印结果
    print("\n========== Dense Search Results ==========")
    print(f"query={query}")
    print(f"cost={cost:.3f}s topk={k}")
    for hit in res[0]:
        pk = hit.get(fields.pk, "")
        score = hit.get("score", None)
        chunk = hit.get(fields.text, "")
        print(f"- pk={pk} score={score}\n  {chunk}\n")


def bm25_dense_hybrid_search(client: MilvusClient, ec: EmbeddingClient, query: str, fields: C.FieldNames, k: int):
    """
    Hybrid Search（dense + BM25 混合检索）。

    ✅ 这里的 BM25 不是 learned sparse！
    - Milvus 的 Full Text Search / BM25 流程是：
      1) collection 中有 text 字段 enable_analyzer=True
      2) schema 定义 BM25 Function：把 text -> sparse（BM25 compatible sparse vector）
      3) sparse 字段建索引：metric_type="BM25"
      4) 搜索时：对 sparse 字段直接传 raw query text（字符串），Milvus 自动做 BM25
    参考官方文档示例：对 sparse 字段 search 时 data 可以直接是 ['query text']。:contentReference[oaicite:1]{index=1}

    关键点：
    - dense 路：data=[dense_vector]（向量）
    - bm25 路：data=[query_text]（字符串）
    - 两路结果用 WeightedRanker 按权重融合排序
    """
    log.info(f"[Hybrid Search: Dense + BM25] query={query}")

    # 1) dense query 向量：用 embedding_service 生成
    q_dense = ec.dense([query])[0]

    # 2) 构造 AnnSearchRequest：dense 路（HNSW）
    req_dense = AnnSearchRequest(
        data=[q_dense],
        anns_field=fields.dense,
        param={"ef": C.HNSW_EF},  # HNSW 搜索深度：越大越准越慢
        limit=k,                 # dense 路候选 top-k
    )

    # 3) 构造 AnnSearchRequest：BM25 路（对 sparse 字段传“原始字符串”）
    #    ✅ 注意：这里 data 放的是 query 字符串，不是 sparse 向量 dict
    #    param 必传（你的 pymilvus 版本要求），BM25 一般用空 dict 即可
    req_bm25 = AnnSearchRequest(
        data=[query],
        anns_field=fields.sparse,  # 这个 sparse 字段必须是 BM25 function 生成的
        param={},                  # 必传；BM25 本身通常无需额外 params
        limit=k,                   # bm25 路候选 top-k
    )

    # 4) WeightedRanker：两路结果加权融合
    #    - HYBRID_DENSE_WEIGHT：语义（dense）权重
    #    - HYBRID_SPARSE_WEIGHT：BM25（字面）权重（你 common.py 里沿用这个常量名即可）
    ranker = _build_weighted_ranker(C.HYBRID_DENSE_WEIGHT, C.HYBRID_SPARSE_WEIGHT)

    # 5) 调 Milvus hybrid_search
    t0 = time.time()
    res = client.hybrid_search(
        collection_name=C.COLLECTION_NAME,
        reqs=[req_dense, req_bm25],
        ranker=ranker,
        limit=k,  # 最终返回 top-k（不是 C.TOPK）
        output_fields=[fields.pk, fields.text],
    )
    cost = time.time() - t0

    # 6) 打印结果
    print("\n====== Hybrid Search Results (Dense + BM25) ======")
    print(f"query={query}")
    print(
        f"cost={cost:.3f}s topk={k} "
        f"weights=[dense:{C.HYBRID_DENSE_WEIGHT}, bm25:{C.HYBRID_SPARSE_WEIGHT}]"
    )
    for hit in res[0]:
        pk = hit.get(fields.pk, "")
        score = hit.get("score", None)
        chunk = hit.get(fields.text, "")
        print(f"- pk={pk} score={score}\n  {chunk}\n")


def filter_search_by_id(client: MilvusClient, query: str, fields: C.FieldNames, k: int):
    """
    filter 精确检索（从 query 中提取 ticket_id，然后按主键/字段过滤查询）。

    适用场景：
    - “问题单号202501031640怎么解决” 这种包含明确 ID 的查询
    - 目标是“必命中某条记录”

    说明：
    - filter 查询本质是结构化检索，不是 ANN。
    - 如果你按主键过滤（pk==id），理论上最多命中 1 条，所以 k 的意义不大；
      但这里仍保留 limit=k 以保持接口一致性。
    """
    log.info(f"[Filter Search] query={query}")

    tid = C.extract_ticket_id(query)
    if not tid:
        # ✅ 不用 sys.exit(1) 静默退出，而是抛异常带原因
        raise ValueError(
            f"检索方式 type=3 需要 query 中包含问题单号/ID，但未提取到。query={query!r}。"
            f"请确认输入包含类似：问题单号202501031640"
        )

    log.info(f"Extracted ticket_id={tid} for filter search.")

    # 用 filter 精确查（这里假设 fields.pk 是 VARCHAR 主键）
    # 注意：Milvus filter 的字符串需要用双引号包起来
    t0 = time.time()
    rows = client.query(
        collection_name=C.COLLECTION_NAME,
        filter=f'{fields.pk} == "{tid}"',
        output_fields=[fields.pk, fields.text],
        limit=k,
    )
    cost = time.time() - t0

    print("\n========== Filter Search Results (pk == id) ==========")
    print(f"query={query}")
    print(f"extracted_id={tid}")
    print(f"cost={cost:.3f}s limit={k}")
    if not rows:
        print("No results matched by filter.")
        return

    for r in rows:
        pk = r.get(fields.pk, "")
        chunk = r.get(fields.text, "")
        print(f"- pk={pk}\n  {chunk}\n")


def main():
    """
    CLI 参数：
    - --q    : 查询问题（必填）
    - --type : 检索方式（必填）
              1=纯 dense
              2=dense + BM25 混合检索
              3=提取 id 做 filter 精确查询
    - --k    : top-k（可选，默认 3）
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--q", required=True, help="查询问题（必填）")
    parser.add_argument(
        "--type",
        required=True,
        type=int,
        choices=[1, 2, 3],
        help="检索方式：1=纯dense  2=dense+bm25混合  3=提取id做filter",
    )
    parser.add_argument("--k", type=int, default=3, help="top-k（可选，默认 3）")

    args = parser.parse_args()

    query: str = args.q
    search_type: int = args.type
    k: int = args.k

    log.info("==== Search Start ====")
    log.info(f"q={query}")
    log.info(f"type={search_type}")
    log.info(f"k={k}")

    # 1) 连接 Milvus
    client = MilvusClient(uri=C.MILVUS_URI)
    log.info(f"Connected to Milvus uri={C.MILVUS_URI}")

    # 2) load collection：确保索引/数据已加载（避免刚启动时查不到或很慢）
    log.info(f"Loading collection: {C.COLLECTION_NAME}")
    client.load_collection(collection_name=C.COLLECTION_NAME)
    log.info("Collection loaded.")

    fields = C.FieldNames()

    # 3) 只有 type=1/2 才需要 dense embedding 服务
    ec: Optional[EmbeddingClient] = None
    if search_type in (1, 2):
        ec = EmbeddingClient(base_url=C.EMBED_BASE_URL, timeout=C.EMBED_TIMEOUT_SEC)

    # 4) 根据 type 路由到不同检索方式
    if search_type == 1:
        # 纯 dense
        assert ec is not None
        dense_search(client, ec, query, fields, k)

    elif search_type == 2:
        # dense + BM25 混合
        assert ec is not None
        try:
            bm25_dense_hybrid_search(client, ec, query, fields, k)
        except Exception as e:
            # 如果你的 collection 不是 BM25 schema，这里很容易报错
            # 给出更明确的提示，方便你定位原因
            log.exception(f"Hybrid(BM25) failed: {e}")
            print("\n[ERROR] dense+bm25 混合检索失败。常见原因：")
            print("1) 你的 collection 没按 Milvus Full Text Search(BM25) 方式建：")
            print("   - text 字段未 enable_analyzer=True")
            print("   - schema 未定义 BM25 Function(text -> sparse)")
            print("   - sparse 字段索引 metric_type 不是 BM25")
            print("2) Milvus / pymilvus 版本过低，不支持 BM25 full text search")
            print("\n建议：先用 type=3（filter）验证单号精确命中，再确认 BM25 的 collection/schema。")
            raise

    else:
        # type == 3：filter by id
        filter_search_by_id(client, query, fields, k)

    log.info("==== Search Done ====")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)

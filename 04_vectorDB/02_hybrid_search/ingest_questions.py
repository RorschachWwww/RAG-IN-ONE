import sys
import time
from typing import Any, Dict, List

from pymilvus import DataType, MilvusClient

import common as C
from embed_client import EmbeddingClient

# 初始化日志器：统一打印 INFO/ERROR 等日志，方便排查全流程问题
log = C.setup_logger("ingest")


def _import_bm25_function_types():
    """
    兼容不同 pymilvus 版本的 Function / FunctionType 导入路径。

    Milvus 的 BM25 Full Text Search 需要在 schema 中定义 FunctionType.BM25：
    - Function：描述“text -> sparse”的内置函数
    - FunctionType：枚举类型，其中 BM25 表示使用 BM25 算法生成稀疏向量
    """
    try:
        # 官方文档常见写法
        from pymilvus import Function, FunctionType
        return Function, FunctionType
    except Exception:
        # 少数版本可能在其他路径（尽量兼容）
        try:
            from pymilvus.client.types import Function, FunctionType  # type: ignore
            return Function, FunctionType
        except Exception as e:
            raise RuntimeError(
                "当前 pymilvus 版本不支持 Function/FunctionType（BM25 Full Text Search）。"
                "请升级：pip install -U pymilvus"
            ) from e


def ensure_collection(
    client: MilvusClient,
    collection: str,
    dense_dim: int,
    overwrite: bool,
    fields: C.FieldNames
) -> None:
    """
    确保 Milvus Collection 存在，并创建/重建索引（BM25 + Dense）。

    ✅ 改造要点（BM25）：
    1) text 字段必须 enable_analyzer=True，Milvus 才能做分词和 BM25 索引
    2) 定义 BM25 Function：把 text 自动转换成 sparse（SPARSE_FLOAT_VECTOR）
    3) sparse 字段的索引 metric_type 必须是 BM25（不是 IP）
       （否则 Milvus 会报 “BM25 function output field must be BM25” 类似错误）
    """
    # 1) 如果 collection 已存在：
    if client.has_collection(collection):
        if overwrite:
            # overwrite=True: 删除旧 collection，重新建（方便多次跑 demo）
            log.info(f"Collection exists, dropping: {collection}")
            client.drop_collection(collection)
        else:
            # overwrite=False: 直接复用旧 collection（不重建 schema/index）
            log.info(f"Collection exists, reuse: {collection}")
            return

    # 2) 创建 schema：定义字段结构
    log.info(f"Creating collection: {collection} (dense_dim={dense_dim})")

    # auto_id=False: 主键由我们自己提供（这里用问题单 ID）
    # enable_dynamic_fields=False: 禁止动态字段，结构更可控
    schema = client.create_schema(auto_id=False, enable_dynamic_fields=False)

    # 主键字段：用 VARCHAR 存储问题单号（或 ID），作为唯一主键
    schema.add_field(field_name=fields.pk, datatype=DataType.VARCHAR, is_primary=True, max_length=128)

    # 文本字段：存 chunk（每条问题单的“信息密度最高”扁平文本）
    # ✅ BM25 要求：必须 enable_analyzer=True（否则无法 BM25）
    # 说明：不指定 analyzer 时，Milvus 默认用 standard analyzer（对中文可能一般）
    # 如需更好的中文分词，需要配置 analyzer（可后续扩展）
    schema.add_field(
        field_name=fields.text,
        datatype=DataType.VARCHAR,
        max_length=65535,
        enable_analyzer=True,
    )

    # dense 向量字段：FLOAT_VECTOR（语义检索用）
    schema.add_field(field_name=fields.dense, datatype=DataType.FLOAT_VECTOR, dim=dense_dim)

    # sparse 向量字段：SPARSE_FLOAT_VECTOR（BM25 用）
    # ✅ 注意：BM25 模式下，这个字段由 Milvus 内置 BM25 Function 自动生成
    # 你插入数据时不需要提供 sparse 字段
    schema.add_field(field_name=fields.sparse, datatype=DataType.SPARSE_FLOAT_VECTOR)

    # 3) 定义 BM25 Function：text -> sparse（自动生成 BM25 sparse embeddings）
    # ✅ 这一步是 “BM25 sparse 的关键”
    Function, FunctionType = _import_bm25_function_types()

    bm25_function = Function(
        name="text_bm25_emb",                # 函数名（任意、但建议有意义）
        input_field_names=[fields.text],     # 输入：text 字段
        output_field_names=[fields.sparse],  # 输出：sparse 字段
        function_type=FunctionType.BM25,     # 使用 BM25 算法生成稀疏向量
    )
    schema.add_function(bm25_function)

    # 4) 创建索引参数
    index_params = client.prepare_index_params()

    # ========== dense 索引（语义）==========
    index_params.add_index(
        field_name=fields.dense,
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200},
        index_name="dense_hnsw",
    )

    # ========== BM25 sparse 索引（全文）==========
    # ✅ 注意 metric_type="BM25"
    # ✅ BM25 支持调参：bm25_k1 / bm25_b（一般默认 1.2 / 0.75）
    index_params.add_index(
        field_name=fields.sparse,
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="BM25",
        params={
            "inverted_index_algo": "DAAT_MAXSCORE",
            "bm25_k1": 1.2,
            "bm25_b": 0.75,
        },
        index_name="bm25_sparse_inverted",
    )

    # 5) 创建 collection（schema + indexes 一次性创建）
    client.create_collection(
        collection_name=collection,
        schema=schema,
        index_params=index_params,
    )
    log.info("Collection created (BM25 + Dense).")


def batch_insert(
    client: MilvusClient,
    collection: str,
    rows: List[Dict[str, Any]],
    ec: EmbeddingClient,
    fields: C.FieldNames,
    batch_size: int = 64,
) -> None:
    """
    批量写入数据到 Milvus（BM25 sparse 自动生成）。

    ✅ 改造要点（BM25）：
    - 不再调用 ec.sparse / ec.both
    - 插入数据时不再写 fields.sparse
    - 只插入：pk + text + dense
      sparse 由 Milvus 在写入时根据 BM25 Function 自动生成
    """
    total = len(rows)
    if total == 0:
        log.warning("No rows to insert.")
        return

    log.info(f"Start inserting rows={total}, batch_size={batch_size}")
    inserted = 0

    # 分批处理，避免一次性 embedding/insert 太大
    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]

        # 1) 主键：问题单 ID（字符串化，避免 None/空白）
        pks = [C.safe_str(r["ID"]) for r in batch]

        # 2) chunk：将每条问题单信息拼成“高信息密度”扁平文本
        chunks = [C.build_chunk(r) for r in batch]

        # 3) dense 向量：只对 chunks 生成（语义检索）
        t0 = time.time()
        dense_vecs = ec.dense(chunks)
        log.info(
            f"Embedding service cost={time.time()-t0:.3f}s "
            f"(dense={len(dense_vecs)})"
        )

        # 4) 构造插入数据
        # ✅ 注意：BM25 模式不需要提供 sparse 字段
        data = []
        for pk, chunk, dv in zip(pks, chunks, dense_vecs):
            data.append(
                {
                    fields.pk: pk,        # 主键
                    fields.text: chunk,   # 原始文本（BM25 会用它生成 sparse）
                    fields.dense: dv,     # dense 向量
                    # fields.sparse:  ❌ 不要写！Milvus 会自动生成 BM25 sparse
                }
            )

        # 5) 插入 Milvus（写入数据）
        t0 = time.time()
        res = client.insert(collection_name=collection, data=data)
        cost = time.time() - t0

        inserted += len(batch)
        log.info(f"Inserted {inserted}/{total}. insert_cost={cost:.3f}s result={str(res)[:160]}...")

    log.info("Insert finished.")


def main():
    """
    主流程（BM25 + Dense）：
    1) 定位 CSV 路径
    2) 读取 CSV 行
    3) 连接 embedding_service（只用于 dense）
    4) probe 获取 dense 向量维度（决定 schema）
    5) 连接 Milvus
    6) 创建/重建 collection（含 BM25 function + BM25 index + dense index）
    7) 批量生成 dense 并 insert（text 直接插入，sparse 自动生成）
    8) load collection（让检索立即可用）
    """
    log.info("==== Ingest Start (BM25 sparse + Dense) ====")
    log.info(f"Project root: {C.get_project_root()}")
    csv_path = C.get_csv_path()
    log.info(f"CSV path    : {csv_path}")

    # 1) 读 CSV（不存在会退出/抛错，取决于你 common.read_csv_rows 的实现）
    rows = C.read_csv_rows(csv_path, log)

    # 2) embedding client（HTTP，只用于 dense）
    ec = EmbeddingClient(base_url=C.EMBED_BASE_URL, timeout=C.EMBED_TIMEOUT_SEC)

    # 3) 探测 dense dim（非常关键：Milvus FLOAT_VECTOR 字段必须写死 dim）
    probe_vec = ec.dense(["probe"])[0]
    dense_dim = len(probe_vec)
    log.info(f"Probed dense_dim={dense_dim}")

    # 4) 连接 Milvus
    client = MilvusClient(uri=C.MILVUS_URI)
    log.info(f"Connected to Milvus uri={C.MILVUS_URI}")

    # 5) 创建/重建 collection（BM25 schema）
    fields = C.FieldNames()
    ensure_collection(client, C.COLLECTION_NAME, dense_dim, C.OVERWRITE_COLLECTION, fields)

    # 6) 批量写入：只插入 pk/text/dense（BM25 sparse 自动生成）
    batch_insert(client, C.COLLECTION_NAME, rows, ec, fields, batch_size=64)

    # 7) load collection
    log.info(f"Loading collection: {C.COLLECTION_NAME}")
    client.load_collection(collection_name=C.COLLECTION_NAME)
    log.info("Collection loaded.")

    log.info("==== Ingest Done ====")


if __name__ == "__main__":
    """
    Python 脚本入口：
    - 捕获异常并打印 traceback，最后以 exit code=1 退出
    - 特殊处理 SystemExit：让 sys.exit(...) 的行为保持原样（不吞掉）
    """
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)

import random
from pymilvus import MilvusClient, DataType

# 模拟生成 768 维向量
def get_random_vector():
    return [random.random() for _ in range(768)]

def scenario_realtime_demo():
    print("\n========== 方案一：实时写入模式（预定义索引） ==========")
    client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    collection_name = "demo_realtime_insert"
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    # 1. 准备 Schema
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("doc_id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=768)

    # 2. 准备索引配置 (Index Params)
    # 关键点：我们在这里就定义好怎么建索引
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128}
    )

    # 3. 创建集合时，直接传入 index_params
    # -------------------------------------------------------
    # 这一步相当于告诉 Milvus：“这个集合从第一天起，所有数据都要按这个规则建索引”
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params  # <--- 关键参数
    )
    print("✓ 集合已创建，且索引规则已预置。")

    # 4. 插入数据
    # Milvus 会自动处理这些数据的索引构建（后台异步或实时处理）
    data = [{"doc_id": i, "vector": get_random_vector()} for i in range(10)]
    client.insert(collection_name=collection_name, data=data)
    print("✓ 数据已插入 (Milvus 自动维护索引)。")

    # 5. 直接搜索
    # 不需要手动调用 create_index，也不需要手动 load (MilvusClient默认行为)
    res = client.search(
        collection_name=collection_name,
        data=[get_random_vector()],
        limit=1,
        consistency_level="Strong"   # 刚插入立即查询，如果不指定一致性，默认是Eventually，这里会查不出来结果。
    )
    print(f"✓ 搜索成功，最近邻ID: {res[0][0]['doc_id']}")

    # 清理
    client.drop_collection(collection_name)

if __name__ == "__main__":
    scenario_realtime_demo()
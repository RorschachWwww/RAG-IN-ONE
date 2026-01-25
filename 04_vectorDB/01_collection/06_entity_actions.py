import random
from pymilvus import MilvusClient, DataType

def entity_operations_demo():
    # 1. 初始化连接
    client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    collection_name = "entity_dynamic_demo"
    partition_name = "vip_zone"

    # 清理环境
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    # 2. 准备 Schema (开启动态字段)
    # -------------------------------------------------------
    # 关键点：enable_dynamic_field=True
    # 这允许我们在后续插入数据时，带上 schema 里没定义的字段
    schema = MilvusClient.create_schema(
        auto_id=False, 
        enable_dynamic_field=True 
    )
    schema.add_field("doc_id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=768)
    # 注意：我们只定义了 doc_id 和 vector 两个字段

    # 准备索引
    index_params = client.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="IVF_FLAT", metric_type="COSINE", params={"nlist": 128})

    # 创建集合
    client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)
    client.create_partition(collection_name=collection_name, partition_name=partition_name)
    print(f"✓ 集合已创建，动态字段支持: Open")

    # =======================================================
    # 3. 场景一：插入包含“动态字段”的数据
    # =======================================================
    print(f"\n--- 场景一：插入动态字段 ---")
    
    # 构造数据：
    # 'source' 和 'publish_year' 根本没在 Schema 里定义！
    # 但因为开了 dynamic_field，它们会被自动接纳并存入 $meta
    data_dynamic = [
        {
            "doc_id": 1001, 
            "vector": [random.random() for _ in range(768)], 
            "source": "Wikipedia",      # <--- 动态字段
            "publish_year": 2024        # <--- 动态字段
        }
    ]
    
    res1 = client.insert(collection_name=collection_name, data=data_dynamic)
    print(f"动态字段插入成功，影响行数: {res1['insert_count']}")
    
    # 验证一下，看看能不能把动态字段查出来
    # 提示：在 output_fields 中可以使用通配符 * 或者指定动态字段名
    check_res = client.query(
        collection_name=collection_name, 
        filter="doc_id == 1001", 
        output_fields=["source", "publish_year"]
    )
    print(f"读取验证 -> source: {check_res[0].get('source')}, year: {check_res[0].get('publish_year')}")

    # =======================================================
    # 4. 场景二：指定分区插入 (Insert to Partition)
    # =======================================================
    print(f"\n--- 场景二：指定分区插入 ---")
    
    data_partition = [
        {"doc_id": 2001, "vector": [random.random() for _ in range(768)], "tag": "VIP_User"}
    ]
    
    res2 = client.insert(
        collection_name=collection_name, 
        data=data_partition, 
        partition_name=partition_name # <--- 指定落入 'vip_zone'
    )
    print(f"插入 '{partition_name}' 分区成功。")

    # =======================================================
    # 5. 场景三：Upsert (覆盖更新)
    # =======================================================
    print(f"\n--- 场景三：Upsert 操作 ---")
    
    # 假设 1001 的 source 信息错了，需要修正
    upsert_data = [
        # 更新 1001 (存在则覆盖)
        {"doc_id": 1001, "vector": [random.random() for _ in range(768)], "source": "Official Doc"}, 
        # 插入 3001 (不存在则新增)
        {"doc_id": 3001, "vector": [random.random() for _ in range(768)], "source": "Blog"}
    ]
    
    res3 = client.upsert(collection_name=collection_name, data=upsert_data)
    print(f"Upsert 操作成功，更新/插入行数: {res3['upsert_count']}")

    # 验证 1001 更新结果
    updated_res = client.query(collection_name=collection_name, filter="doc_id == 1001", output_fields=["source"])
    print(f"验证 1001 更新后的 source: {updated_res[0]['source']} (预期: Official Doc)")

    # 清理
    client.drop_collection(collection_name)

if __name__ == "__main__":
    entity_operations_demo()
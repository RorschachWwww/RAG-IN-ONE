import time
import random
from pymilvus import MilvusClient, DataType

def get_random_vector():
    return [random.random() for _ in range(768)]

def scenario_bulk_load_demo():
    print("\n========== 方案二：批量导入模式（先插后建） ==========")
    client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    collection_name = "demo_bulk_load"
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    # 1. 准备 Schema (同上)
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("doc_id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=768)

    # 2. 创建集合 (注意：这里不传 index_params)
    # -------------------------------------------------------
    # 关键点：此时集合是“裸奔”状态，没有任何索引负担
    client.create_collection(
        collection_name=collection_name,
        schema=schema
        # index_params 缺省
    )
    print("✓ 集合已创建 (无索引状态)。")

    # 3. 第一阶段：批量导入历史数据 (Bulk Load)
    # 此时写入速度最快，因为不需要计算索引
    print("... 正在模拟大规模数据写入 (1000条) ...")
    bulk_data = [{"doc_id": i, "vector": get_random_vector()} for i in range(1000)]
    client.insert(collection_name=collection_name, data=bulk_data)
    print("✓ 历史数据写入完成。")

    # 4. 第二阶段：手动构建索引 (Build Index)
    # -------------------------------------------------------
    # 数据导完了，现在开始根据所有数据计算索引，并立下“规矩”
    print("... 开始构建索引 (开启自动化流水线) ...")
    
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128}
    )
    
    # 显式调用 create_index
    client.create_index(
        collection_name=collection_name,
        index_params=index_params
    )
    print("✓ 索引构建完成！历史数据已整理完毕。")

    # 5. 加载集合 (Load)
    # 构建完索引后，需要加载到内存才能搜
    client.load_collection(collection_name)

    # 6. 第三阶段：验证后续自动化 (New Inserts)
    # -------------------------------------------------------
    # 重点验证：后续新插入的数据，不需要再手动 create_index
    print("\n... 模拟第二天新进来了 5 条数据 ...")
    new_data = [{"doc_id": 2000+i, "vector": get_random_vector()} for i in range(5)]
    client.insert(collection_name=collection_name, data=new_data)
    print("✓ 新数据已插入。")

    # 7. 搜索验证
    # 我们特意搜一下刚才新插入的数据，证明它已经被系统接管了
    print("... 尝试搜索新插入的数据 ...")
    # 这里我们直接用新数据的向量去搜，看看能不能搜到它自己
    target_vec = new_data[0]["vector"] 
    res = client.search(
        collection_name=collection_name,
        data=[target_vec],
        limit=1
    )
    
    found_id = res[0][0]['id']
    print(f"✓ 搜索结果 ID: {found_id} (预期: 2000)")
    
    if found_id == 2000:
        print("★ 验证成功：索引规则生效中，新数据已被自动纳入搜索范围，无需再次手动建索引！")

    # 清理
    client.drop_collection(collection_name)

if __name__ == "__main__":
    scenario_bulk_load_demo()
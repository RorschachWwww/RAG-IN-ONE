from pymilvus import MilvusClient

def collection_lifecycle_demo():
    """
    Milvus 集合(Collection) 核心操作演示
    展示集合的创建、数据写入以及“加载/释放”的资源管理机制。
    """
    
    # 1. 初始化客户端连接
    # -------------------------------------------------------
    client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    
    collection_name = "production_collection_demo"

    # 环境清理：确保演示环境纯净
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    # 2. 创建集合 (Create)
    # -------------------------------------------------------
    # 在不显式定义 Schema 的快速模式下，只需指定向量维度。
    # Milvus 会自动初始化主键字段 'id' 和向量字段 'vector'。
    print(f"\n--- [Step 1] 创建集合: {collection_name} ---")
    client.create_collection(
        collection_name=collection_name,
        dimension=768  # 指定向量维度为 768
    )
    print(f"集合已创建。当前状态：仅元数据存在，无数据实体。")

    # 3. 写入数据 (Insert)
    # -------------------------------------------------------
    # 向集合中写入演示数据。
    # 注意：此时数据已写入持久化存储（Disk/MinIO），但尚未加载到查询内存中。
    print(f"\n--- [Step 2] 写入数据 ---")
    data = [
        {"id": 1001, "vector": [0.1] * 768, "source": "paper_A"},
        {"id": 1002, "vector": [0.2] * 768, "source": "paper_B"}
    ]
    res = client.insert(collection_name=collection_name, data=data)
    print(f"写入完成，影响行数: {res['insert_count']}")

    # 4. 加载集合 (Load) - 关键操作
    # -------------------------------------------------------
    # 将数据从持久化存储热加载到 Query Node 内存中。
    # 只有执行了 Load 操作，集合才具备可检索性 (Searchable)。
    print(f"\n--- [Step 3] 加载集合 (Load) ---")
    client.load_collection(collection_name)
    print("集合状态变更: Loaded (内存驻留，服务就绪)。")

    # (此时可执行 search/query 操作...)

    # 5. 释放集合 (Release) - 关键操作
    # -------------------------------------------------------
    # 将数据从内存中卸载，释放计算资源，但保留磁盘数据。
    # 适用于冷备数据或非高频访问的业务场景。
    print(f"\n--- [Step 4] 释放集合 (Release) ---")
    client.release_collection(collection_name)
    print("集合状态变更: Released (内存已释放，不可检索)。")

    # 6. 删除集合 (Drop)
    # -------------------------------------------------------
    # 物理删除集合及其包含的所有数据。
    print(f"\n--- [Step 5] 删除集合 ---")
    client.drop_collection(collection_name)
    print("集合已物理删除。")

if __name__ == "__main__":
    collection_lifecycle_demo()
from pymilvus import MilvusClient, DataType

def schema_definition_demo():
    # ——————————————
    # 0. 连接 Milvus
    # ——————————————
    client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
    collection_name = "schema_structure_demo"
    
    # 清理旧数据，确保演示环境纯净
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    # ——————————————
    # 1. 创建 Schema 对象
    # ——————————————
    # auto_id=False: 表示我们将手动管理主键 ID
    # enable_dynamic_field=True: 允许存储 Schema 定义之外的动态字段
    schema = MilvusClient.create_schema(
        auto_id=False, 
        enable_dynamic_field=True,
        description="包含多模态向量与丰富标量的全功能 Schema"
    )
    print("✓ 已创建基础 Schema 对象")

    # ——————————————
    # 2. 定义主键 (Primary Key)
    # ——————————————
    # 必须指定一个主键，此处使用 Int64 类型
    schema.add_field(
        field_name="doc_id",
        datatype=DataType.INT64,
        is_primary=True,
        description="文档唯一标识 ID"
    )
    print("✓ 已添加主键字段: doc_id")

    # ——————————————
    # 3. 定义 2 种向量字段 (Vector Fields)
    # ——————————————
    # [向量 1] 稠密浮点向量 (Float Vector)
    # 场景：用于存储文本 embedding，是最常用的向量类型
    schema.add_field(
        field_name="dense_vector",
        datatype=DataType.FLOAT_VECTOR,
        dim=768,
        description="768维文本语义向量"
    )

    # [向量 2] 二进制向量 (Binary Vector)
    # 场景：用于图像指纹或哈希去重
    # 注意：dim 指的是比特位数 (Bits)，128 bit 对应 16 字节
    schema.add_field(
        field_name="binary_hash",
        datatype=DataType.BINARY_VECTOR,
        dim=128,
        description="128位二进制哈希向量"
    )
    print("✓ 已添加向量字段: dense_vector, binary_hash")

    # ——————————————
    # 4. 定义 5 种标量字段 (Scalar Fields)
    # ——————————————
    # [标量 1] 字符串 (VarChar)
    schema.add_field(
        field_name="title", 
        datatype=DataType.VARCHAR, 
        max_length=256,
        description="文档标题"
    )

    # [标量 2] 整数 (Int32)
    schema.add_field(
        field_name="publish_year", 
        datatype=DataType.INT32,
        description="发布年份"
    )

    # [标量 3] 布尔值 (Bool)
    schema.add_field(
        field_name="is_reviewed", 
        datatype=DataType.BOOL,
        description="审核状态"
    )

    # [标量 4] JSON 对象 (JSON)
    # 用于存储结构灵活的元数据，如 {"author": "Alex", "source": "web"}
    schema.add_field(
        field_name="meta_info", 
        datatype=DataType.JSON,
        description="扩展元信息"
    )

    # [标量 5] 数组 (Array)
    # 用于存储多值属性，如文章的多个标签 ["Tech", "AI"]
    schema.add_field(
        field_name="tags",
        datatype=DataType.ARRAY,
        element_type=DataType.VARCHAR, # 声明数组内部存的是字符串
        max_capacity=10,               # 数组最多包含 10 个元素
        max_length=50,                 # 每个元素最长 50 字符
        description="标签列表"
    )
    print("✓ 已添加标量字段: title, publish_year, is_reviewed, meta_info, tags")

    # ——————————————
    # 5. 使用 Schema 创建 Collection
    # ——————————————
    print(f"\n--- 正在创建集合: {collection_name} ---")
    
    # 将定义好的 Schema 传入，正式创建集合容器
    client.create_collection(
        collection_name=collection_name,
        schema=schema
    )
    print("✓ 集合创建成功，Schema 结构已生效。")

    # ——————————————
    # 6. 查看 Collection 详情
    # ——————————————
    # 获取并打印集合的详细信息，验证字段结构是否符合预期
    desc = client.describe_collection(collection_name)
    print(f"\n[集合详情验证]:")
    print(f" - 字段总数: {len(desc['fields'])} (包含自动生成的隐藏字段)")
    for field in desc['fields']:
        # 简单打印字段名和类型 ID
        print(f" - Field: {field['name']}, Type: {field['type']}")

    # 清理环境
    client.drop_collection(collection_name)
    print("\n✓ 演示结束，已清理测试集合。")

if __name__ == "__main__":
    schema_definition_demo()
from pymilvus import MilvusClient

def database_management_demo():
    """
    Milvus 数据库(Database)管理全流程演示
    包含：连接、创建、列出、修改属性、切换、删除
    """
    
    # =======================================================
    # 1. 初始化连接 (默认连接到 'default' 数据库)
    # =======================================================
    # 这里的 uri 指向你 Docker 部署的本地 Milvus 地址
    print("\n--- 1. 连接到 Milvus ---")
    client = MilvusClient(uri="http://localhost:19530", token="root:Milvus") 
    # 注意：如果你没有修改过配置，docker版默认是不开启鉴权的，token可以省略。
    # 如果开启了鉴权，默认是 root:Milvus
    
    # 定义我们要演示的数据库名称
    demo_db_name = "my_demo_database"

    # =======================================================
    # 2. 查 (List): 查看当前所有数据库
    # =======================================================
    print(f"\n--- 2. 列出当前所有数据库 ---")
    dbs = client.list_databases()
    print(f"当前数据库列表: {dbs}")

    # 为了演示顺利，如果之前存在同名数据库，先清理掉
    if demo_db_name in dbs:
        print(f"检测到 {demo_db_name} 已存在，正在清理以确保演示纯净...")
        # 注意：删除数据库前，必须确保数据库内没有 Collection (集合)
        # 这里假设它是空的直接删除，实际生产中要先循环 drop_collection
        client.drop_database(demo_db_name)

    # =======================================================
    # 3. 增 (Create): 创建数据库
    # =======================================================
    print(f"\n--- 3. 创建新数据库: {demo_db_name} ---")
    
    # 创建数据库。
    # Milvus 的 Database 创建相对简单，不像 Collection 那样需要定义复杂的 Schema。
    # 这里的 properties 是可选参数，用于存储一些自定义的元数据键值对。
    client.create_database(
        db_name=demo_db_name,
        properties={"owner": "demo_user", "priority": "high"} 
    )
    print(f"数据库 {demo_db_name} 创建成功！")

    # =======================================================
    # 4. 改 (Alter): 修改数据库属性
    # =======================================================
    # 注意：你不能直接“重命名”数据库。
    # 这里的“改”通常指的是修改数据库的 Properties (元数据/配置属性)。
    print(f"\n--- 4. 修改数据库属性 (Alter) ---")
    
    # 比如我们想给这个数据库增加一个属性，或者修改之前的属性
    client.alter_database(
        db_name=demo_db_name,
        properties={"priority": "critical", "description": "for_wechat_article_demo"}
    )
    
    # 验证修改结果（通过 describe_database 查看详细信息）
    db_info = client.describe_database(demo_db_name)
    print(f"修改后的数据库信息: {db_info}")

    # =======================================================
    # 5. 切换/使用数据库 (Use)
    # =======================================================
    print(f"\n--- 5. 切换/使用指定数据库 ---")
    
    # 在 MilvusClient 中，要操作特定数据库，推荐的方式是实例化一个新的 Client 指向该 DB。
    # 这样后续所有的 create_collection, search 等操作都会在这个 DB 下进行。
    db_specific_client = MilvusClient(
        uri="http://localhost:19530", 
        db_name=demo_db_name  # <--- 这里指定数据库
    )
    
    # 验证一下我们是否真的在用新数据库
    # 我们在新数据库里建一个极简的 Collection 试试
    # 这是一个“隐性”验证：如果在 list_collections 里能看到，说明切换成功
    if not db_specific_client.list_collections():
        print(f"当前连接的数据库 ({demo_db_name}) 为空，切换成功。")

    # =======================================================
    # 6. 删 (Drop): 删除数据库
    # =======================================================
    print(f"\n--- 6. 删除数据库: {demo_db_name} ---")
    
    # 注意：Milvus 规定，删除数据库前，该数据库必须是空的（没有任何 Collection）。
    # 如果里面有表，必须先 drop_collection。
    
    # 因为我们刚才只是切过去看了一眼，没建表，所以可以直接删。
    db_specific_client.close() # 先关闭针对该库的连接
    
    client.drop_database(demo_db_name)
    print(f"数据库 {demo_db_name} 已删除。")
    
    # 最终确认
    final_dbs = client.list_databases()
    print(f"最终数据库列表: {final_dbs}")

if __name__ == "__main__":
    try:
        database_management_demo()
    except Exception as e:
        print(f"\n发生错误: {e}")
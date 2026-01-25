from FlagEmbedding import BGEM3FlagModel

if __name__ == '__main__':
    # 1. 加载模型
    print("--- 正在加载模型 ---")
    model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

    # 2. 定义文档
    sentences = [
        "BGE-M3 is an embedding model supporting dense, sparse, and multi-vector retrieval.", 
        "BGE-M3 是一个支持密集检索、稀疏检索和多向量检索的嵌入模型。"
    ]

    # 3. 执行推理
    print("--- 开始推理 ---")
    output = model.encode(
        sentences, 
        return_dense=True, 
        return_sparse=True, 
        return_colbert_vecs=True
    )

    print("\n" + "="*50)
    print("   BGE-M3 结果直观展示")
    print("="*50)

    # --- 1. 密集向量 (Dense) ---
    # 作用：把整句话压缩成一个向量，用来做模糊语义匹配
    dense_vec = output['dense_vecs'][0]
    print(f"\n[1. 密集向量 (Dense)]")
    print(f"   > 形状: {dense_vec.shape} (整句话被压缩成了1个1024维的数组)")
    print(f"   > 数据预览(前10位): {dense_vec[:10]} ...")
    print("   > 解读: 这一串数字代表了整句话的'语义摘要'。")

    # --- 2. 稀疏向量 (Sparse) ---
    # 作用：类似于提取关键词，权重越高代表这个词对这句话越重要
    print(f"\n[2. 稀疏向量 (Sparse)] - 关键词权重分析")
    
    # 获取第一句话的权重字典
    sparse_weight_dict = model.convert_id_to_token(output['lexical_weights'][0])
    
    # 【优化】: 按权重从高到低排序，看看模型认为哪些词最重要
    sorted_weights = sorted(sparse_weight_dict.items(), key=lambda x: x[1], reverse=True)
    
    print("   > 模型认为最重要的词 (Top 5):")
    for token, weight in sorted_weights[:5]:
        print(f"     - '{token}': {weight:.4f}")
    
    print(f"   > 原始字典长度: {len(sparse_weight_dict)} 个Token")
    print("   > 解读: 你可以看到 'BGE'、'model'、'retrieval' 等实词的权重很高，")
    print("          而 'is'、'an' 等停用词的权重很低。这就是稀疏检索的原理。")

    # --- 3. 多向量 (Multi-Vector) ---
    # 作用：不压缩句子，保留每个Token的独立向量，用于精细对比
    colbert_vec = output['colbert_vecs'][0]
    print(f"\n[3. 多向量 (Multi-Vector)]")
    print(f"   > 形状: {colbert_vec.shape}")
    print(f"   > 解释: 形状是 (Token数, 1024)。")
    print(f"          这句话被切分成了 {colbert_vec.shape[0]} 个Token，每个Token都有自己的独立向量。")
    print("   > 解读: 它可以捕捉到“词与词”之间的细微交互，比密集向量更精准，但占空间更大。")

    print("\n" + "="*50)

    # 显式停止，防止报错
    model.stop_self_pool()
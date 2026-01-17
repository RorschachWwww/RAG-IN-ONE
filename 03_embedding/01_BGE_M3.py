
from FlagEmbedding import BGEM3FlagModel

# 1. 加载模型
# use_fp16=True 可以加快计算并节省显存
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# 2. 定义待处理的文档
sentences = [
    "BGE-M3 is an embedding model supporting dense, sparse, and multi-vector retrieval.", 
    "BGE-M3 是一个支持密集检索、稀疏检索和多向量检索的嵌入模型。"
]

# 3. 执行推理
# 开启所有三个返回选项
output = model.encode(
    sentences, 
    return_dense=True, 
    return_sparse=True, 
    return_colbert_vecs=True
)

# --- 结果展示 ---

# 1. 密集向量 (Dense)
# 传统的语义向量，通常用于向量数据库 (Milvus/Pinecone)
# 形状: [batch_size, 1024]
print(f"Dense Embedding Shape: {output['dense_vecs'].shape}")
# 示例输出: (2, 1024)

# 2. 稀疏向量 (Sparse)
# 类似于词袋模型，但带有权重，用于混合检索 (Hybrid Search)
# 格式: 字典列表，key是token ID，value是权重
print(f"\nSparse Embedding (First Doc):")
print(model.convert_id_to_token(output['lexical_weights'][0]))
# 示例输出: {'BGE': 0.52, 'M3': 0.48, 'embedding': 0.35, ...}

# 3. 多向量 (Multi-Vector / ColBERT)
# 为每个 Token 生成向量，用于高精度的重排序阶段
# 形状: List of [seq_len, 1024]
print(f"\nMulti-Vector Shape (First Doc): {output['colbert_vecs'][0].shape}")
# 示例输出: (16, 1024) - 假设第一句话分词后有16个token
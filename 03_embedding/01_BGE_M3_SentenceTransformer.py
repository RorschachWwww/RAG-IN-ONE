from sentence_transformers import SentenceTransformer

# 1. 加载模型
# device 可以指定为 'cuda', 'mps' (Mac), 'cpu'
model = SentenceTransformer("BAAI/bge-m3", device="cpu")

# 2. 准备数据
sentences = ["什么是RAG？", "RAG的全称是Retrieval-Augmented Generation"]

# 3. 执行推理
embeddings = model.encode(sentences, normalize_embeddings=True)

# 4. 输出维度验证
print(f"向量维度: {embeddings.shape}") 
# BGE-M3 默认维度通常为 1024
print(f"第一句话的向量前5位: {embeddings[0][:5]}")
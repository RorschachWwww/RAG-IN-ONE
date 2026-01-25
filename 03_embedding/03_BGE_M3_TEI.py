import time
from langchain_huggingface import HuggingFaceEndpointEmbeddings

# 1. 配置 TEI 服务地址
# 这里的 URL 就是你部署的容器地址
TEI_SERVICE_URL = "http://localhost:8080"

def get_dense_embeddings_via_tei():
    print(f"🚀 正连接 TEI 服务: {TEI_SERVICE_URL} ...")
    
    # 2. 初始化 LangChain 的 Embedding 类
    embeddings = HuggingFaceEndpointEmbeddings(
        model=TEI_SERVICE_URL,
        task="feature-extraction" 
    )

    # 3. 准备测试文本
    sentences = [
        "BGE-M3 是一个支持多语言的强大模型。",
        "TEI 提供了生产级的高性能推理服务。"
    ]

    # 4. 调用服务
    start = time.time()
    # embed_documents 会自动处理批次发送
    dense_vecs = embeddings.embed_documents(sentences)
    cost = (time.time() - start) * 1000

    # 5. 打印结果
    print(f"✅ 成功获取稠密向量 (Dense Embeddings)")
    print(f"   - 耗时: {cost:.2f} ms")
    print(f"   - 向量数量: {len(dense_vecs)}")
    print(f"   - 向量维度: {len(dense_vecs[0])} (BGE-M3 默认为 1024)")
    print(f"   - 向量示例 (前5位): {dense_vecs[0][:5]}")

if __name__ == "__main__":
    try:
        get_dense_embeddings_via_tei()
    except Exception as e:
        print(f"❌ 调用失败，请检查容器是否启动: {e}")
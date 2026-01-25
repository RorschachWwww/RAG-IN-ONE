import os
from openai import OpenAI

# 1. 初始化客户端
# 生产环境中，API Key 应从环境变量读取，严禁硬编码
client = OpenAI(
    api_key="sk-xxxxxxxxxxxxxxxx", 
    # base_url="...", # 如需通过代理访问，可在此配置 base_url
)

def get_embedding(text: str, model: str = "text-embedding-3-small"):
    """
    调用 OpenAI API 获取文本向量
    
    Args:
        text: 输入文本
        model: 模型名称 (默认为 text-embedding-3-small)
        
    Returns:
        list: 浮点数构成的向量列表
    """
    # 数据清洗：移除换行符是 Embedding 任务中的常见最佳实践
    text = text.replace("\n", " ")
    
    try:
        # 发送请求
        response = client.embeddings.create(
            input=[text], 
            model=model
        )
        
        # 提取向量
        # response.data[0] 对应 input 列表中的第一条文本
        return response.data[0].embedding
        
    except Exception as e:
        print(f"API 调用异常: {e}")
        return []

if __name__ == "__main__":
    test_content = "RAG技术通过检索增强生成，解决了大模型的幻觉问题。"
    
    vector = get_embedding(test_content)
    
    if vector:
        print(f"输入文本: {test_content}")
        print(f"向量维度: {len(vector)}") # text-embedding-3-small 默认维度为 1536
        print(f"向量前5位示例: {vector[:5]}")
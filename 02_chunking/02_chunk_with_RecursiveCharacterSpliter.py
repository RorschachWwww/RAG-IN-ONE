from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../documents/china_history/唐朝历史介绍.md')
# 1. 直接加载文档
loader = TextLoader(file_path, encoding="utf-8")
data = loader.load()

# 2.初始化切分器
splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,          # 适当放大，足以容纳一两个完整的长句
    chunk_overlap=30,        # 增加重叠，保证上下文衔接
    # 关键：增加了中文句号、问号、以及Markdown的标题分隔符
    separators=[
        "\n\n",   # 第一优先级：段落
        "\n",     # 第二优先级：换行
        "。",     # 第三优先级：中文句号
        "！",     # 第四优先级：感叹号
        "？",     # 第五优先级：问号
        " ",      # 第六优先级：空格
        ""        # 最后手段：字符切分
    ]
)

# 执行切分
chunks = splitter.split_documents(data)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:\n{chunk.page_content}\n{'-'*20}")
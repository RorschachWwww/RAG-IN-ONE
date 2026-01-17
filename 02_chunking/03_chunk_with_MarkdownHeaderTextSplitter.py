import os
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.document_loaders import TextLoader

# 1. 读取文档内容
#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../documents/china_history/唐朝历史介绍.md')

loader = TextLoader(file_path, encoding="utf-8")
data = loader.load()

# 2. 定义切分规则：将 Markdown 的标题层级映射为元数据（Metadata）中的键名
# 这样检索时，每个 Chunk 都会知道它属于哪个大标题和子标题
headers_to_split_on = [
    ("#", "一级标题"),
    ("##", "二级标题"),
    ("###", "三级标题"),
]

# 3. 初始化切分器并执行切分
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False # 设置为 False 可以保留正文中的标题行，提高 LLM 的阅读连贯性
)

# 4. 手动处理 Document 列表
all_header_splits = []

for doc in data:
    # 从 Document 对象中提取字符串内容进行切分
    header_splits = markdown_splitter.split_text(doc.page_content)
    
    # 【进阶小技巧】：手动把 TextLoader 自带的元数据（如 source）加回去
    for split in header_splits:
        split.metadata.update(doc.metadata)
        
    all_header_splits.extend(header_splits)

# 5. 查看结果
print(f"切分完成，共生成 {len(all_header_splits)} 个块。\n")

for i, chunk in enumerate(all_header_splits):
    print(f"--- Chunk {i+1} ---")
    # 现在元数据里既有“标题”，又有“source”了
    print(f"【元数据】: {chunk.metadata}")
    print(f"【内容片段】: {chunk.page_content.strip()}...") 
    print("\n")
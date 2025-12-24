from langchain_unstructured import UnstructuredLoader
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
markdown_path = os.path.join(current_dir, '../../documents/china_history/唐朝历史介绍.md')

loader = UnstructuredLoader(
    file_path=markdown_path,
    mode="elements"   # 关键：按结构元素解析
)

docs = loader.load()

print(f"文档数量: {len(docs)}\n")

for i, doc in enumerate(docs[:8]):
    print(f"--- Document {i} ---")
    # print("category:", doc.metadata.get("category"))
    print("metadata:", doc.metadata)
    print("text:", doc.page_content[:200])
    print()

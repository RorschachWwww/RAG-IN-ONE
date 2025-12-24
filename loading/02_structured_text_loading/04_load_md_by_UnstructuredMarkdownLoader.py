import os
from langchain_community.document_loaders import UnstructuredMarkdownLoader

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
markdown_path = os.path.join(current_dir, '../../documents/china_history/唐朝历史介绍.md')

loader = UnstructuredMarkdownLoader(markdown_path)
docs = loader.load()
print(f"Number of documents: {len(docs)}\n")
print(docs[0].page_content[:250])

loader = UnstructuredMarkdownLoader(markdown_path, mode="elements")
data = loader.load()
print(f"Number of documents: {len(data)}\n")
for document in data:
    print(f"{document}\n")

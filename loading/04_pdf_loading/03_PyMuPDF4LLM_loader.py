from langchain_pymupdf4llm import PyMuPDF4LLMLoader
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/pdf/阿里巴巴Java开发手册.pdf')

loader = PyMuPDF4LLMLoader(file_path)

# 2. 加载文档
# 默认会将每一页解析为一个独立的 LangChain Document 对象
pages = loader.load()

for page in pages[:4]:
# 3. 查看页面的内容（已经是 Markdown 格式了！）
    print(f"第{page.metadata['page']}页内容:")
    print(page.page_content)
    print(f"第{page.metadata['page']}页元数据:")
    print(page.metadata)

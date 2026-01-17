from langchain_community.document_loaders import PyPDFLoader
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/pdf/阿里巴巴Java开发手册.pdf')

loader = PyPDFLoader(file_path)
pages = loader.load()
print(f"加载了 {len(pages)} 页PDF文档")
print("只打印前5页内容：")
for page in pages[:4]:
    print(page.page_content)

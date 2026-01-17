import os
from langchain_community.document_loaders import TextLoader

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/china_history/唐朝诗人.json')

text_loader = TextLoader(file_path, encoding='utf-8')
text_documents = text_loader.load()

print(text_documents)
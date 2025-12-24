import os
from langchain_community.document_loaders import TextLoader

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
print(current_dir)
#构造文件路径
file_path = os.path.join(current_dir, '../../documents/china_history/china_history.txt')
print(file_path)
#加载文件
loader = TextLoader(file_path, encoding='utf-8')
#读取文件
docs = loader.load()
#打印文件内容
print(docs)
import os
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import TextLoader

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/china_history')

loader = DirectoryLoader(file_path,     
                         glob="**/*.md",     # 匹配所有子目录下的.md文件
                         loader_cls=lambda path: TextLoader(path, encoding="utf-8")) # 指定加载工具        

#读取文件
docs = loader.load()
#打印加载的文件数量
print(f"加载的文件数量: {len(docs)}")
#打印第一个文件的内容
print(docs[0])
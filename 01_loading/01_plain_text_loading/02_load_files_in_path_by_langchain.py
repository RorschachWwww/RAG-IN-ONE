"""
下面的代码会扫描documents/china_history文件夹下所有文件，在Windows系统下运行会因为Poppler/Tesseract未安装而报错。
Windows 环境非常容易在 Poppler/Tesseract 上踩坑，且安装适配过程复杂，建议在 Linux 环境下运行。如果只是想要在Windows环境看一下效果，可以暂时把pdf文件移出目录。
"""
import os
from langchain_community.document_loaders import DirectoryLoader

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/china_history')

#加载文件夹下所有文件
loader = DirectoryLoader(file_path)
#读取文件
docs = loader.load()
#打印加载的文件数量
print(f"加载的文件数量: {len(docs)}")
#打印第一个文件的内容
print(docs[0])

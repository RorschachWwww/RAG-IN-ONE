from langchain_community.document_loaders import UnstructuredImageLoader
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
image_path = os.path.join(current_dir, '../../documents/load_picture/rag-pic.jpg')

loader = UnstructuredImageLoader(image_path,
    strategy="ocr_only")

data = loader.load()
print(data)

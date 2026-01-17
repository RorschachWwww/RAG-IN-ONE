from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../documents/others/log.txt')
# 1. 直接加载文档
loader = TextLoader(file_path, encoding="utf-8")
data = loader.load()

# 2. 初始化分块器
text_splitter = CharacterTextSplitter(
    separator = "\n",       # 关键点：显式指定用单换行符切分
    chunk_size = 200,        # 目标块大小
    chunk_overlap = 10      # 重叠大小
)

# 3. 切分文档
all_splits = text_splitter.split_documents(data)

print(f"已处理文档，切分出 {len(all_splits)} 个段落。")
print(f"第一个段落的字符数: {len(all_splits[0].page_content)}")
print(f"第一个段落的内容: \n{all_splits[0].page_content}")

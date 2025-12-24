import os
from langchain_community.document_loaders import JSONLoader

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/china_history/唐朝诗人.json')

print("=== 1.文档信息 ===")
theme_loader = JSONLoader(file_path = file_path, 
                          jq_schema='"文档标题：" + .fileTitle + "，内容概要：" + .theme',
                          text_content=True)

theme_docs = theme_loader.load()
print(theme_docs)

print("\n\n")

print("=== 2.诗人介绍 ===")
poets_loader = JSONLoader(file_path = file_path,
                           jq_schema='.poets[] | "姓名：" + .name + "，出生年月：" + .lifespan + "，作品风格：" + .style',
                           text_content=True)

poets_docs = poets_loader.load()
print(poets_docs)

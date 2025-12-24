from typing import Any


import pymupdf
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
file_path = os.path.join(current_dir, '../../documents/pdf/阿里巴巴Java开发手册.pdf')

# 打开PDF文件
doc = pymupdf.open(file_path)
# text = [page.get_text() for page in doc]
# print(text)

# 示例: 使用PyMuPDF的基础功能
print("=== PyMuPDF 基本信息提取 ===")
print(f"文档页数: {len(doc)}")
print(f"文档标题: {doc.metadata['title']}")
print(f"文档作者: {doc.metadata['author']}")
print(f"文档元数据: {doc.metadata}")  # 比Unstructured提供更多元数据

# 只遍历前4页
for page_num, page in enumerate[Any](doc[:4]):
    # 提取文本
    text = page.get_text()
    
    print(f"\n--- 第{page_num + 1}页 ---")
    print("文本内容:", text[:500])  # 显示前500个字符
    
    # 提取图片
    images = page.get_images()
    print(f"图片数量: {len(images)}")
    
    # 获取页面链接
    links = page.get_links()
    print(f"链接数量: {len(links)}")
    
    # 获取页面大小
    width, height = page.rect.width, page.rect.height
    print(f"页面尺寸: {width} x {height}")

doc.close()
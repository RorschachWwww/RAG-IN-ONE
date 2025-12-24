from langchain_core.documents import Document
import pytesseract
from PIL import Image
import os

#获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
#构造文件夹路径
image_path = os.path.join(current_dir, '../../documents/china_history/3.jpeg')

# 1. 打开图片
image = Image.open(image_path)

# 2. 指定中文 OCR
# 支持简体中文
text = pytesseract.image_to_string(image, lang="chi_sim")

# 3. 封装为 LangChain Document
doc = Document(page_content=text, metadata={"source": image_path})

# 4. 输出
print(doc.page_content)
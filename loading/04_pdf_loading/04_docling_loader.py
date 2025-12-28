import os
from langchain_docling import DoclingLoader
from langchain_docling.interfaces import ExportType
from docling.document_converter import DocumentConverter, PdfPipelineOptions
from docling.datamodel.pipeline_options import TableFormerMode

# --- 核心配置：一次性解决安永报告的三大解析难题 ---

pipeline_options = PdfPipelineOptions()

# 【解决问题 1：典型的侧边栏干扰】
# 开启 OCR 与视觉布局分析。它会将页面边缘的“EY 安永”等水印识别为 Aside（旁注）
# 从而在提取正文时自动过滤掉这些干扰项，避免噪声进入检索块。
pipeline_options.do_ocr = True 

# 【解决问题 3：跨页与嵌套表格】
# 针对报告第 4、14 页那种“没框线但有逻辑”的视觉表格，开启精准模式。
# 它能将安永报告中的细分子行业对比分析，还原为 Markdown 的表格结构。
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE 

# 初始化转换器
converter = DocumentConverter(pipeline_options=pipeline_options)

# --- 进入 LangChain 流程 ---

# 【解决问题 2：复杂的混合排版（核心重点）】
# 针对报告图 3（行业发展格局）这种文字围绕图标分布的非线性布局：
# 关键在于 ExportType.MARKDOWN。
# Docling 会利用视觉模型判断“阅读流”，将原本碎裂的文字块按照“政策->需求->竞争->技术”
# 的逻辑顺序重新串联，而不是按照物理坐标生硬拼接。
loader = DoclingLoader(
    file_path="安永_智启新质生产力之三.pdf",
    converter=converter,
    export_type=ExportType.MARKDOWN  # 强制进行逻辑线性化转换
)

# 执行解析
docs = loader.load()

# --- 验证解析结果 ---
# 此时生成的 docs[0].page_content 已经是干净、有序、带有结构化表格的 Markdown 了
print(f"成功解决安永报告中的三大排版挑战！")
print(f"解析后的文本片段预览：\n{docs[0].page_content[:1500]}")
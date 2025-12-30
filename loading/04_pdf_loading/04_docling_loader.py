import os
# 1. 修正后的 LangChain 集成导入
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_core.documents import Document

# 2. Docling 核心配置导入
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

# --- 核心配置：一次性解决安永报告的三大解析难题 ---

pipeline_options = PdfPipelineOptions()

# 【解决问题 1：页眉页脚与侧边栏干扰】
pipeline_options.do_ocr = True 

# 【解决问题 3：跨页与无线框嵌套表格】
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE 

# 初始化转换器
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

# --- 路径处理 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, '../../documents/pdf/安永医疗AIGC报告.pdf')
output_base_dir = os.path.join(current_dir, "output_markdown")
if not os.path.exists(output_base_dir):
    os.makedirs(output_base_dir)

# --- 进入 LangChain 流程 ---

# 【解决问题 2：复杂的混合排版与逻辑阅读顺序】
# 注意：这里我们传入了配置好的自定义 converter
loader = DoclingLoader(
    file_path=file_path,
    converter=converter,
    export_type=ExportType.MARKDOWN 
)

print(f"🚀 LangChain 正在通过 Docling 加载并解析文档...")

# --- 核心改造：既要满足 LangChain 格式，又要分页保存 ---

# 1. 使用 loader 加载（这步是 RAG 的标准动作，会解析全图逻辑）
# 实际上 loader.load() 会触发转换，我们可以通过 result 拿到分页数据
# 为了演示分页导出，我们直接获取 loader 内部触发后的结果
result = converter.convert(file_path)

# 2. 循环每一页：生成 LangChain Document 对象并同步保存到本地
langchain_docs = []

for page_no, page in result.document.pages.items():
    # 导出当前页的 Markdown 文本
    page_markdown = result.document.export_to_markdown(page_no=page_no)
    
    # 构造 LangChain 标准 Document 对象（方便后续接 VectorStore）
    doc = Document(
        page_content=page_markdown,
        metadata={
            "source": file_path,
            "page": page_no,
            "title": "安永医疗AIGC报告"
        }
    )
    langchain_docs.append(doc)
    
    # 同步保存到物理文件
    file_name = f"安永报告_第{page_no:02d}页.md"
    save_path = os.path.join(output_base_dir, file_name)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(page_markdown)
    
    print(f"已生成: {file_name} 并封装为 LangChain Document")

# --- 验证结果 ---
print(f"\n✅ 全部解析完成！")
print(f"LangChain 内存中已加载 {len(langchain_docs)} 个分页文档对象。")
print(f"物理文件已保存在: {output_base_dir}")
import re
import os
import pandas as pd
from io import StringIO
from langchain_community.document_loaders import UnstructuredPDFLoader

def extract_billionaire_tables(pdf_path):
    # 1. 配置 UnstructuredLoader
    print("正在初始化 Loader...")
    loader = UnstructuredPDFLoader(
        pdf_path,
        mode="elements", 
        strategy="hi_res", # 必须使用 hi_res 才能获得准确的表格HTML结构
        infer_table_structure=True, 
    )

    print("正在加载并解析 PDF，这可能需要一点时间（取决于文件大小和机器性能）...")
    docs = loader.load()

    # 2. 定义提取逻辑（状态机）
    extracted_tables = []
    current_year = None
    
    # 匹配年份标题 (例如 "2025", "2024")
    year_pattern = re.compile(r'^\s*20[0-2][0-9]\s*$')

    # 3. 遍历文档流
    for doc in docs:
        category = doc.metadata.get('category', '')
        content = doc.page_content.strip()

        # 逻辑 A: 寻找年份标题
        if (category == 'Title' or category == 'NarrativeText') and year_pattern.match(content):
            current_year = content.strip()
            print(f"-> 发现年份上下文: {current_year}")
            continue

        # 逻辑 B: 提取表格
        if category == 'Table':
            if current_year:
                # 获取表格的 HTML 格式
                table_html = doc.metadata.get('text_as_html', None)
                
                extracted_tables.append({
                    "year": current_year,
                    "content_text": content, # 原始文本作为备用
                    "content_html": table_html # 核心结构化数据
                })
            else:
                pass

    return extracted_tables

def save_tables_to_markdown(tables, output_file, target_years):
    """
    将提取的表格转换为 Markdown 格式并保存到文件
    """
    print(f"\n正在将数据写入 {output_file} ...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 全球亿万富翁排行榜数据汇总\n\n")
        
        for item in tables:
            year = item['year']
            if year in target_years:
                f.write(f"## {year} 年全球亿万富翁排行榜\n\n")
                
                # 尝试将 HTML 转换为标准的 Markdown 表格
                html_content = item.get('content_html')
                
                if html_content:
                    try:
                        # 使用 Pandas 读取 HTML 表格
                        dfs = pd.read_html(StringIO(html_content))
                        if dfs:
                            # 取第一个表格，并转换为 markdown
                            # index=False 去掉 pandas 的行索引
                            md_table = dfs[0].to_markdown(index=False)
                            f.write(md_table)
                            f.write("\n\n")
                            print(f"成功转换 {year} 年表格为 Markdown 格式。")
                        else:
                            # HTML 解析为空，回退到纯文本
                            f.write("```text\n")
                            f.write(item['content_text'])
                            f.write("\n```\n\n")
                    except Exception as e:
                        print(f"HTML转换失败 ({year}): {e}，回退到纯文本。")
                        f.write("```text\n")
                        f.write(item['content_text'])
                        f.write("\n```\n\n")
                else:
                    # 没有 HTML 数据，写入纯文本
                    f.write("```text\n")
                    f.write(item['content_text'])
                    f.write("\n```\n\n")
                
                f.write("---\n\n")

# --- 执行提取并保存结果 ---

# 获取当前脚本所在目录的相对路径 
current_dir = os.path.dirname(os.path.abspath(__file__))
pdf_file_path = os.path.join(current_dir, "../../documents/pdf/The_World's_Billionaires.pdf")  
output_md_path = "billionaires_tables.md"

try:
    if not os.path.exists(pdf_file_path):
        print(f"错误: 找不到文件 {pdf_file_path}")
    else:
        # 1. 提取数据
        tables = extract_billionaire_tables(pdf_file_path)
        
        # 2. 设定目标年份
        target_years = ["2023", "2024", "2025"]

        # 3. 保存为 Markdown
        save_tables_to_markdown(tables, output_md_path, target_years)
        
        print(f"\n处理完成！请查看生成的文档: {output_md_path}")

except Exception as e:
    print(f"\n发生严重错误: {e}")
    print("提示: 确保安装了 `pip install pandas lxml tabulate` 以及 `unstructured[pdf]`")
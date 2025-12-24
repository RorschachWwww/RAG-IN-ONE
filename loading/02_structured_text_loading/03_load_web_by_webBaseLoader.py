# 使用WebBaseLoader加载网页
import bs4
from langchain_community.document_loaders import WebBaseLoader
page_url = "https://book.douban.com/subject/4913064/"
# loader = WebBaseLoader(web_paths=[page_url])
# docs = []
# docs = loader.load()
# assert len(docs) == 1
# doc = docs[0]
# print(f"===metadata===\n{doc.metadata}\n")
# print(f"===page_content===\n{doc.page_content}\n")


# 只解析文章的主体部分
loader = WebBaseLoader(
    web_paths=[page_url],
    bs_kwargs={
        "parse_only": bs4.SoupStrainer(id="wrapper"),
    },
    bs_get_text_kwargs={"separator": "\n", "strip": True},
)
docs = loader.load()

print(docs)
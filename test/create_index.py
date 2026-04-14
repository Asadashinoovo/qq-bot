from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
import os
# 1. 从data.txt加载文档
data_path = "D:/Projects/mai-bot/mai-bot/data/data.txt"

with open(data_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 按分割线分割文本，获取每个元素
texts = [text.strip() for text in content.split("=" * 60) if text.strip()]

docs = [Document(page_content=t) for t in texts]

embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.environ.get('dashscope_api_key')
)

# 2. 创建向量存储并保存到本地  faiss_index_store
vectorstore = FAISS.from_documents(docs, embeddings)

local_faiss_path = "./faiss_index_store"
vectorstore.save_local(local_faiss_path)

print(f"已创建并保存 {len(docs)} 个文档的FAISS索引到 {local_faiss_path}")

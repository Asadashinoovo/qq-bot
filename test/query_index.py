from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
import os
# 1. 加载已保存的索引/faiss_index_store
embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.environ.get('dashscope_api_key')
)
local_faiss_path = "./faiss_index_store"

loaded_vectorstore = FAISS.load_local(
    local_faiss_path,
    embeddings,
    allow_dangerous_deserialization=True
)

# 2. 输入查询文本
query = "哪知精灵更强"


# 3. 执行相似性搜索
results = loaded_vectorstore.similarity_search(query, k=5)

print(f"\n查询: '{query}'")
print("相似度最高的文档:")
for i, doc in enumerate(results, 1):
    print(f"{i}. {doc.page_content}")

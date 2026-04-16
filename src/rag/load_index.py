from langchain_community.vectorstores import FAISS
import os
from nonebot import logger

def load_rag(embeddings, index_path: str):
    """
    加载 FAISS 索引。

    Args:
        embeddings: 向量模型（如 DashScopeEmbeddings 实例）
        index_path: 索引文件目录路径

    Returns:
        FAISS vector store 对象，加载失败返回 None
    """
    if os.path.exists(index_path):
        try:
            vector_store = FAISS.load_local(
                index_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("RAG 索引加载成功")
            return vector_store
        except Exception as e:
            logger.info(f"RAG 索引加载失败: {e}")
            return None
    else:
        logger.info("未找到 RAG 索引文件")
        return None

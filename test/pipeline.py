from unstructured.partition.auto import partition
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from collections import Counter
import os


def run_pipeline(
    input_path: str = "D:/Projects/mai-bot/mai-bot/pachong/comments_output.txt",
    output_data_path: str = "D:/Projects/mai-bot/mai-bot/data/data.txt",
    output_faiss_path: str = "D:/Projects/mai-bot/mai-bot/faiss_index_store",
) -> dict:
    """
    完整流水线：解析文档 -> 清洗数据 -> 创建FAISS向量索引

    Args:
        input_path: 原始文件路径（支持txt等）
        output_data_path: 解析后文本的保存路径
        output_faiss_path: FAISS索引的保存路径

    Returns:
        包含各阶段统计信息的字典
    """
    # --- 阶段1：解析文档 ---
    print(f"[阶段1] 解析文档: {input_path}")

    # 删除旧数据文件
    if os.path.exists(output_data_path):
        os.remove(output_data_path)
        print(f"  已删除旧数据文件: {output_data_path}")

    elements = partition(filename=input_path, content_type="application")

    total_chars = sum(len(str(e)) for e in elements)
    types = Counter(e.category for e in elements)
    print(f"  解析完成: {len(elements)} 个元素, {total_chars} 字符")
    print(f"  元素类型: {dict(types)}")

    # 保存解析结果
    with open(output_data_path, 'w', encoding='utf-8') as f:
        f.write(f"解析完成: {len(elements)} 个元素, {total_chars} 字符\n")
        f.write(f"元素类型: {dict(types)}\n")
        f.write("\n所有元素:\n")
        for i, element in enumerate(elements, 1):
            f.write(f"Element {i} ({element.category}):\n")
            f.write(str(element))
            f.write("\n" + "=" * 60 + "\n")
    print(f"  解析数据已保存到: {output_data_path}")

    # --- 阶段2：加载并清洗数据 ---
    print(f"[阶段2] 加载并清洗数据: {output_data_path}")
    with open(output_data_path, 'r', encoding='utf-8') as f:
        content = f.read()

    texts = [text.strip() for text in content.split("=" * 60) if text.strip()]
    docs = [Document(page_content=t) for t in texts]
    print(f"  清洗完成: {len(docs)} 个文档")

    # --- 阶段3：创建FAISS向量索引 ---
    print(f"[阶段3] 创建FAISS向量索引: {output_faiss_path}")

    # 删除旧索引文件
    import shutil
    if os.path.exists(output_faiss_path):
        shutil.rmtree(output_faiss_path)
        print(f"  已删除旧索引: {output_faiss_path}")

    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=os.environ.get('dashscope_api_key')
    )
    vectorstore = FAISS.from_documents(
        docs, 
        embeddings,
        distance_strategy="MAX_INNER_PRODUCT"
    )
    vectorstore.save_local(output_faiss_path)
    print(f"  索引已保存到: {output_faiss_path}")

    return {
        "elements_count": len(elements),
        "total_chars": total_chars,
        "element_types": dict(types),
        "docs_count": len(docs),
        "faiss_path": output_faiss_path,
    }


if __name__ == "__main__":
    result = run_pipeline()
    print(f"\n流水线执行完成: {result}")

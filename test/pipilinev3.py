import os
import shutil
import faiss
import numpy as np
from unstructured.partition.auto import partition
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
import tiktoken


def run_pipeline_with_inspection(
    input_path: str = "D:/Projects/mai-bot/mai-bot/pachong/comments_output.txt",
    output_faiss_path: str = "D:/Projects/mai-bot/mai-bot/faiss_index_store",
    output_chunks_path: str = "D:/Projects/mai-bot/mai-bot/data/debug_chunks.txt",
    min_chunk_len: int = 30,
    chunk_size: int = 384,
    chunk_overlap: int = 64,
    hnsw_M: int = 32,
    hnsw_efConstruction: int = 40,
    hnsw_efSearch: int = 16,
) -> dict:
    print(f"[🚀 启动 RAG 数据流水线] {os.path.basename(input_path)}")

    # 1. 解析原始数据
    print("[1/4] 解析原始数据...")
    elements = partition(filename=input_path, content_type="application")
    print(f"  ✅ 解析完成: {len(elements)} 个原子元素")

    # 2. 过滤噪声
    valid_texts = []
    for elem in elements:
        text = str(elem).strip()
        if len(text) >= min_chunk_len and text.replace(" ", ""):
            valid_texts.append(text)
    print(f"  ✅ 过滤后保留: {len(valid_texts)} 个有效文本段")

    # 3. 语义分块
    print("[2/4] 执行语义分块...")
    enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(t: str) -> int: return len(enc.encode(t))

    combined_text = "\n\n".join(valid_texts)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        length_function=count_tokens,
        keep_separator=True
    )
    chunks = splitter.split_text(combined_text)
    final_chunks = [c for c in chunks if count_tokens(c) >= 15]
    print(f"  ✅ 分块完成: {len(final_chunks)} 个块")

    # 4. 导出分块审查文件
    print("[3/4] 生成分块可视化报告...")
    with open(output_chunks_path, 'w', encoding='utf-8') as f:
        f.write("=== RAG 分块审查报告 ===\n")
        f.write(f"总块数: {len(final_chunks)} | 策略: size={chunk_size}, overlap={chunk_overlap}\n")
        f.write("=" * 90 + "\n\n")

        for i, chunk in enumerate(final_chunks):
            tok = count_tokens(chunk)
            char = len(chunk)
            start_preview = chunk[:60].replace('\n', ' ')
            end_preview = chunk[-60:].replace('\n', ' ') if len(chunk) > 60 else ""

            f.write(f"[Chunk {i+1:03d}/{len(final_chunks)}] | Tokens: {tok:4d} | Chars: {char:4d}\n")
            f.write(f"▶ 开头: {start_preview}...\n")
            f.write(f"◀ 结尾: ...{end_preview}\n")
            f.write("─" * 90 + "\n")
            f.write(chunk)
            f.write("\n\n" + "═" * 90 + "\n\n")

    print(f"  ✅ 审查文件已导出: {output_chunks_path}")

    # 5. 构建 FAISS（HNSW 索引）
    print("[4/4] 向量化并构建 HNSW 索引...")
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=os.environ.get("dashscope_api_key")
    )
    docs = [Document(page_content=c, metadata={"chunk_id": i}) for i, c in enumerate(final_chunks)]

    if os.path.exists(output_faiss_path):
        shutil.rmtree(output_faiss_path)

    # 构建基础索引，并转为余弦相似度（归一化后内积等价于余弦）
    vector_store = FAISS.from_documents(
        docs,
        embeddings,
        distance_strategy="COSINE"  # 归一化后 HNSW 的 L2 距离等价于余弦相似度
    )

    # 替换为 HNSW 索引
    d = vector_store.index.d
    hnsw_index = faiss.IndexHNSWFlat(d, hnsw_M)
    hnsw_index.hnsw.construction_ef = hnsw_efConstruction
    hnsw_index.hnsw.search_ef = hnsw_efSearch

    # 复制向量数据到 HNSW 索引（需要手动归一化，因为 COSINE 模式只在搜索时归一化）
    vectors = vector_store.index.reconstruct_n(0, vector_store.index.ntotal)
    faiss.normalize_L2(vectors)  # 归一化后，L2 距离等价于余弦相似度（范围 0-2）
    hnsw_index.add(vectors)
    vector_store.index = hnsw_index

    vector_store.save_local(output_faiss_path)
    print(f"  ✅ HNSW 索引已保存: {output_faiss_path} (M={hnsw_M}, efConstruction={hnsw_efConstruction}, efSearch={hnsw_efSearch})")

    return {
        "chunks_saved": output_chunks_path,
        "faiss_saved": output_faiss_path,
        "total_chunks": len(docs)
    }


if __name__ == "__main__":
    result = run_pipeline_with_inspection()
    print(f"\n📊 流水线统计: {result}")

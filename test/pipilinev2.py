import os
import shutil
import tiktoken
from unstructured.partition.auto import partition
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document

def run_pipeline_with_inspection(
    input_path: str = "D:/Projects/mai-bot/mai-bot/pachong/comments_output.txt",
    output_faiss_path: str = "D:/Projects/mai-bot/mai-bot/faiss_index_store",
    output_chunks_path: str = "D:/Projects/mai-bot/mai-bot/data/debug_chunks.txt",  # 🎯 分块审查文件
    min_chunk_len: int = 30,
    chunk_size: int = 384,
    chunk_overlap: int = 64,
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

    # 4. 🎯 导出分块审查文件（核心新增）
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
            f.write(chunk)  # 完整内容
            f.write("\n\n" + "═" * 90 + "\n\n")

    print(f"  ✅ 审查文件已导出: {output_chunks_path}")
    print(f"  💡 建议用 VSCode / Notepad++ 打开，搜索 `[Chunk ` 快速跳转")

    # 5. 构建 FAISS
    print("[4/4] 向量化并构建索引...")
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=os.environ.get("dashscope_api_key")
    )
    docs = [Document(page_content=c, metadata={"chunk_id": i}) for i, c in enumerate(final_chunks)]
    
    if os.path.exists(output_faiss_path):
        shutil.rmtree(output_faiss_path)
        
    FAISS.from_documents(
        docs, 
        embeddings,
        distance_strategy="MAX_INNER_PRODUCT"
    ).save_local(output_faiss_path)
    
    print(f"  ✅ 索引已保存: {output_faiss_path}")

    return {
        "chunks_saved": output_chunks_path,
        "faiss_saved": output_faiss_path,
        "total_chunks": len(docs)
    }


if __name__ == "__main__":
    result = run_pipeline_with_inspection()
    print(f"\n📊 流水线统计: {result}")
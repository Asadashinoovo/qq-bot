from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import elements_to_json

# 文件路径
pdf_path = "D:/Projects/mai-bot/mai-bot/pachong/comments_output.txt"

# 使用Unstructured加载并解析文档
elements = partition(
    filename=pdf_path,
    content_type="application"
)

# 打印解析结果
print(f"解析完成: {len(elements)} 个元素, {sum(len(str(e)) for e in elements)} 字符")

# 统计元素类型
from collections import Counter
types = Counter(e.category for e in elements)
print(f"元素类型: {dict(types)}")

# 保存到data/data.txt
output_path = "D:/Projects/mai-bot/mai-bot/data/data.txt"

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"解析完成: {len(elements)} 个元素, {sum(len(str(e)) for e in elements)} 字符\n")
    f.write(f"元素类型: {dict(types)}\n")
    f.write("\n所有元素:\n")
    for i, element in enumerate(elements, 1):
        f.write(f"Element {i} ({element.category}):\n")
        f.write(str(element))
        f.write("\n" + "=" * 60 + "\n")

print(f"数据已保存到: {output_path}")
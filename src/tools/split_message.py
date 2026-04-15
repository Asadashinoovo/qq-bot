import json
import re
from nonebot import logger
from src.config.llmconfig import llmmodel

MAX_CHARS = 50
MAX_SEGMENTS = 4

AT_PATTERN = r'@\d+'
AT_REGEX = re.compile(AT_PATTERN)

SYSTEM_PROMPT = """你是一个QQ群聊消息拆分助手。请将用户输入的长文本拆分成适合发送的短消息段落。

规则：
- 每段不超过 50 个字符
- 条数不固定，由你根据内容判断（1-4条）
- 在自然语义断点切分（逗号、句号、换行处）
- 保持语义完整，不要截断词语
- **重要：绝对不能删除或遗漏任何 @提及 和 URL 图片地址**
- 返回JSON数组格式，每项是一段字符串
- 例如：["第一段内容", "第二段内容", "第三段内容"]
"""

def _validate_segments(original: str, segments: list[str]) -> bool:
    """
    校验切分后的段落是否丢失了 @提及 或 URL。
    返回 True 表示通过，False 表示失败需降级。
    """
    # 统计原始文本中的 @ 提及数量
    original_ats = AT_REGEX.findall(original)
    # 统计切分后所有段落中的 @ 提及数量
    segments_text = "".join(segments)
    segment_ats = AT_REGEX.findall(segments_text)

    if len(original_ats) != len(segment_ats):
        return False
    return True


async def split_message_for_human(text: str) -> list[str]:
    """
    调用 LLM 将长文本切分为适合人类发送的短段落。

    Args:
        text: 原始文本（未做 @ 转换，纯字符串）

    Returns:
        list[str]: 切分后的文本段落列表，如果失败则返回原文本单段列表
    """
    if not text or len(text.strip()) == 0:
        return []

    # 如果文本已经很短，直接返回
    if len(text) <= MAX_CHARS:
        return [text]

    try:
        response = await llmmodel.ainvoke(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": f"请拆分以下文本：\n{text}"}]
        )
        content = response.content.strip()

        # 尝试解析 JSON 数组
        # 去掉可能的 markdown 代码块
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0].strip()

        segments = json.loads(content)

        # 验证格式
        if isinstance(segments, list) and all(isinstance(s, str) for s in segments):
            # 确保不超过最大条数
            segments = segments[:MAX_SEGMENTS]

            # 校验 @ 提及是否丢失
            if not _validate_segments(text, segments):
                # 降级：返回原文本，不切分
                return [text]

            return segments
        else:
            return [text]

    except Exception as e:
        logger.warning(f"split_message_for_human failed: {e}")
        return [text]
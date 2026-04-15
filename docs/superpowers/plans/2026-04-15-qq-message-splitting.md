# QQ 消息分片发送实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LLM 返回的文本按语义切分为 1-4 条短消息，每条不超过 50 字，依次发送，最后一条附带图片，间隔 1 秒，模拟真人发送习惯。

**Architecture:** 在 `qqagentbot.py` 的 handler 中，`_process_pollinations_url` 之后新增 `split_message_for_human()` 函数调用 LLM 做语义切分，然后分条发送。拆分逻辑独立成工具函数，复用现有 `llmmodel`。

**Tech Stack:** nonebot2, LangChain, QQ OneBot v11 适配器

---

## 文件结构

- **Create:** `src/tools/split_message.py` — 独立的分片工具函数
- **Modify:** `src/plugins/qqagentbot.py:259-275` — 替换原有的单条发送逻辑为分片发送逻辑

---

## Task 1: 创建 split_message.py 分片工具

**Files:**
- Create: `src/tools/split_message.py`

- [ ] **Step 1: 编写 split_message_for_human 函数**

```python
import os
import json
import re
from src.config.llmconfig import llmmodel

MAX_CHARS = 50
MAX_SEGMENTS = 4
MIN_SEGMENTS = 1

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

    except Exception:
        # 降级：返回原文本
        return [text]
```

- [ ] **Step 2: 提交**

```bash
git add src/tools/split_message.py
git commit -m "feat: add split_message_for_human for QQ message splitting"
```

---

## Task 2: 集成到 qqagentbot.py

**Files:**
- Modify: `src/plugins/qqagentbot.py:259-275`

- [ ] **Step 1: 添加 import**

在文件顶部添加（如果尚未存在）：
```python
import asyncio
from src.tools.split_message import split_message_for_human
```

- [ ] **Step 2: 替换发送逻辑**

找到现有的发送逻辑（约 259-275 行）：
```python
text_part, img_list, is_succeed = await _process_pollinations_url(str(context))
# ... 原有单条发送逻辑 ...
```

替换为分片发送逻辑：
```python
text_part, img_list, is_succeed = await _process_pollinations_url(str(context))

if is_succeed is False:
    await llm.send(Message("图片服务器连接超时了哦，请稍后再试"))
    return

# 先切分文本（基于原始 text_part，避免 Message 对象干扰切分）
segments = await split_message_for_human(text_part or "")

    for i, segment in enumerate(segments):
        # 每段单独做 @ 转换（parse_at_mentions 返回 Message）
        msg = await parse_at_mentions(bot, int(group_id), segment)
        # 最后一条附带所有图片
        if i == len(segments) - 1 and img_list:
            for pathfile in img_list:
                msg.append(MessageSegment.image(Path(pathfile).as_uri()))
        await llm.send(msg)
        # 最后一条之后不需要等待
        if i < len(segments) - 1:
            await asyncio.sleep(1)
```

- [ ] **Step 3: 提交**

```bash
git add src/plugins/qqagentbot.py
git commit -m "feat: integrate split_message_for_human into qqagentbot handler"
```

---

## 验证

- [ ] 本地运行 nonebot，检查启动无报错
- [ ] 手动发送一条长消息（如 200 字），确认拆分成多条发送
- [ ] 确认 @ 提及在第一条
- [ ] 确认图片在最后一条
- [ ] 确认消息间隔约 1 秒

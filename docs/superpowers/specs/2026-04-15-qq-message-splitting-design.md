# QQ 消息分片发送设计

## 背景

在 QQ 群聊场景中，bot 需要将 LLM 返回的长文本拆分成多条短消息发送，模拟真人发送习惯，提升用户体验。

## 需求

- 每条消息不超过 50 字
- 条数随机：1-4 条（不固定，更拟人）
- 按 LLM 语义切分，在自然断点（逗号、句号、换行处）切断
- 第一条包含 @ 提及信息
- 最后一条附带所有图片
- 每条消息间隔 1 秒

## 发送流程

```
agent 输出
  → _process_pollinations_url() → text_part + img_list
  → parse_at_mentions() → 纯文字（带 @ 转换）
  → split_message_for_human() → 1-4 段文本
  → 第一条：@ + 第一段文字
  → 中间条：纯文字
  → 最后条：剩余文字 + 所有图片
  → 每条间隔 1 秒发送
```

## 新增函数

### split_message_for_human()

```python
async def split_message_for_human(text: str) -> list[str]:
    """
    调用 LLM 将长文本切分为适合人类发送的短段落。

    切分策略：
    - 条数随机 1-4 条（由 LLM 根据内容判断）
    - 每段不超过 50 字
    - 在自然语义断点切分

    Returns:
        list[str]: 切分后的文本段落列表
    """
```

### 集成点

在 `qqagentbot.py` 的 `llm` handler 中，259 行后：

```python
text_part, img_list, is_succeed = await _process_pollinations_url(str(context))

final_text = await parse_at_mentions(bot, int(group_id), text_part or "")

segments = await split_message_for_human(final_text)

for i, segment in enumerate(segments):
    msg = Message(segment)
    # 最后一条附带所有图片
    if i == len(segments) - 1 and img_list:
        for pathfile in img_list:
            msg.append(MessageSegment.image(Path(pathfile).as_uri()))
    await llm.send(msg)
    if i < len(segments) - 1:
        await asyncio.sleep(1)
```

## 边界情况处理

| 情况 | 处理方式 |
|------|----------|
| 原文 <= 50 字 | 直接 1 条发送，不切分 |
| 切分 LLM 调用失败 | 降级为原文直接发送（1 条，图片放末尾） |
| 没有图片 | 正常发送纯文字 |
| @ 提及 | 在第一条包含，后续条不含 |

## 错误处理

- 切分 LLM 调用失败时，降级为单条发送原文，保留 @ 和图片逻辑
- 不因切分失败而中断整个 handler

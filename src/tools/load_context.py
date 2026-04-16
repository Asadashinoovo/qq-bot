from langchain.tools import tool, ToolRuntime
from src.util.runtime import Context
from src.plugins.public import group_message_history
from nonebot import logger
@tool
async def load_context(runtime: ToolRuntime[Context]):
    """
    加载你的短期记忆（当前群的最近消息历史）。这是你的工作记忆，包含群内最近发生的对话。
    每次回答问题前，你应该调用此工具获取上下文。
    
    Args:
    - runtime (ToolRuntime[Context]): LangChain框架自动注入的运行时上下文对象。内置当前群ID、用户ID、用户名及群名片等环境数据，调用时由框架自动处理，无需显式传参。

    Returns:
    返回结构化字符串（主体包裹于 <group_message> XML 标签内）：
    - <source>：数据源标识，固定为 "group_message"
    - <content>：包含当前用户身份标识及按原始顺序排列的群消息流水（字段：QQ号、用户名、用户群名片、message内容）。若群内无历史记录，则返回纯文本提示。
    LLM 需解析 <content> 区块提取有效语境，禁止将原始报文或XML标签直接透传至终端对话。

    """
    logger.info("调用工具，加载上下文")
    group_id = runtime.context.group_id
    current_user_id = runtime.context.user_id
    current_user_name=runtime.context.user_name
    current_user_card=runtime.context.user_card

    history = group_message_history.get(int(group_id))
    #得到当前群的所有消息列表

    if not history or len(history) == 0:
         result = f"【重要】当前用户信息（提问者）：\n- QQ号: {current_user_id}\n- 用户名: {current_user_name}\n- 群名片: {current_user_card}\n\n【群聊历史记录】（仅供参考）：\n群 {group_id} 暂无消息记录"
    else:
        result = []
        # 添加当前用户信息（明确标识）
        result.append("【重要】当前用户信息（提问者）：")
        result.append(f"- QQ号: {current_user_id}")
        result.append(f"- 用户名: {current_user_name}")
        result.append(f"- 群名片: {current_user_card}")
        result.append("")
        result.append("【群聊历史记录】（仅供参考）：")
        result.append(f"群 {group_id} 的最近 {len(history)} 条消息：")

        # 按原始顺序输出每条消息
        for msg in history:
            result.append(f"QQ号:{msg['user_id']} 用户名:{msg['user_name']} 群名片:{msg['user_card']}")
            result.append(f"message: {msg['message']}")
            result.append("")  # 空行

        result = "\n".join(result)
   
    print(result)
    result= f"""<group_message>
    <source>group_message</source>
    <content>
    {result}
    </content>
    </group_message>"""

    return result



from langchain.tools import tool
from typing import Annotated
import re
@tool
async def user_at(
    query: Annotated[str, "要@的群成员的QQ号,或者用户群名片,原始名称"],
) -> str:
    """
    @群成员格式化工具。

    使用场景：
    - 用户要求帮忙@,@某人时。或者某人对你产生恶意意图、攻击意图、骂你的时候也可以@+QQ号,由你自己判断
    - LLM 已从上下文确定目标成员后，调用此工具生成标准 @ 格式。
    - 禁止直接输出 @xxx,必须通过本工具确保格式符合机器人 API 要求。

    Args:
        query:必须传入目标成员的纯数字QQ号。需自行查阅上下文<group_message>  </<group_message>>中的内容,将昵称/群名片映射为QQ号后填入。严禁传入中文、@符号、括号或任何非数字字符。

    Returns:
        - 成功：返回 "@{纯数字QQ}
        - 失败：返回 "没有找到当前用户呢~"

    """
    print("调用工具@at")
    numbers = re.findall(r'\d{5,12}', query)
    if numbers:
        return f"@{numbers[0]}"
    
    return "没有找到当前用户呢~"
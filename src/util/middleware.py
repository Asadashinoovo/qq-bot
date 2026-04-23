from langchain.agents.middleware import before_agent,after_agent
from langchain.agents.middleware import AgentState
from langchain.tools import ToolRuntime
from src.util.runtime import Context
from src.util.custom_exception import PromptInjectionError
from typing import Any
import re


@before_agent
async def first_layer_security(state: AgentState,runtime: ToolRuntime[Context]):
    msg=runtime.context.msg

    # 常见提示词注入模式正则表达式
    injection_patterns = [
        # 忽略之前的指令
        r'忽略.*指令',
        r'ignore.*previous.*instruction',
        r'disregard.*above',

        # 绕过限制
        r'绕过.*限制',
        r'bypass.*restriction',
        r'override.*safety',
        r'忽略.*安全',
        r'do.*anything.*ask',

        # 反向注入
        r'repeat.*above',
        r'echo.*previous',
        r'复制.*前面的',
    ]

    # 检查消息是否匹配任何注入模式
    msg_lower = msg.lower()
    for pattern in injection_patterns:
        if re.search(pattern, msg_lower):
            print(f"检测到提示词注入: {pattern}")
            raise PromptInjectionError("检测到提示词注入，拒绝执行")

    # 可选：打印正常消息用于调试
    # print(f"安全检查通过: {msg}")
    



@after_agent
def testafter(state: AgentState,runtime: ToolRuntime[Context])->dict[str, Any] | None:
    a=1
    
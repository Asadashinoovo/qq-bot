from langchain_core.runnables.config import RunnableConfig

# 全局默认配置（可复用）
DEFAULT_AGENT_CONFIG: RunnableConfig = {
    "recursion_limit": 12,          #  防死循环：LLM 最多决策 12 次工具调用
    "timeout": 45,                  #  总超时(秒)：覆盖 LLM + 所有工具执行时间
    ##"max_concurrency": 6,           #  限制单请求内工具并发数，防下游 API 限流
    "metadata": {
        "app": "qq-bot",
        "trace": True,              # 配合 LangSmith 或自定义日志中间件
        "env": "production"
    },
    "tags": ["agent-v1", "group-chat"],
    "return_intermediate_steps": False  #  生产关闭，节省内存/网络开销
}
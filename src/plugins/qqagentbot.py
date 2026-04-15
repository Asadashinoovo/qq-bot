from langchain.agents import create_agent
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, Bot, MessageSegment
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.params import EventMessage
from langchain.tools import tool
from src.plugins.public import group_message_history, parse_at_mentions
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain_community.embeddings import DashScopeEmbeddings
from src.rag.load_index import load_rag
from langchain.agents.middleware import before_agent,after_agent
from langchain.agents.middleware import AgentState
from src.tools.load_image import load_image
from src.config.llmconfig import llmmodel
from src.plugins import system_prompt
from src.agents.agent_config import DEFAULT_AGENT_CONFIG
from src.tools.load_image import create_image
import re,httpx,os,time,asyncio
from pathlib import Path
from src.tools.user_at import user_at
from src.tools.split_message import split_message_for_human
from nonebot import logger
from src.util.image_utils import _process_pollinations_url

PROMPT = system_prompt.PROMPT



@dataclass
class Context:
    group_id: str
    user_id: str
    user_name: str
    user_card :str
    msg :str
    bot :Bot
    


def load_memory(group_id,current_user_id,current_user_name,current_user_card):
    """
    加载100条群聊信息
    
    Returns:
    返回结构化字符串（主体包裹于 <group_message> XML 标签内）：
    - <source>：数据源标识，固定为 "group_message"
    - <content>：包含当前用户身份标识及按原始顺序排列的群消息流水（字段：QQ号、用户名、用户群名片、message内容）。若群内无历史记录，则返回纯文本提示。
    LLM 需解析 <content> 区块提取有效语境，禁止将原始报文或XML标签直接透传至终端对话。

    """
    logger.info("开始加载上下文")
  
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
        result.append(f"群 {group_id} 的最近 {len(history)} 条消息：\n")

        # 按时间倒序输出，最新的消息在前（LLM attention 更集中在末尾）
        for msg in reversed(history):
            seconds_ago = int(time.time()) - msg["time"]
            if seconds_ago < 60:
                time_str = f"{seconds_ago}秒前"
            elif seconds_ago < 3600:
                time_str = f"{seconds_ago // 60}分钟前"
            elif seconds_ago < 86400:
                time_str = f"{seconds_ago // 3600}小时前"
            else:
                time_str = f"{seconds_ago // 86400}天前"
            result.append(f"[{time_str}] QQ号:{msg['user_id']} 用户名:{msg['user_name']} 群名片:{msg['user_card']}")
            result.append(f"message: {msg['message']}")
            result.append("")  # 空行

        result = "\n".join(result)
     
    result= f"""<group_message>
    <source>group_message</source>
    <content>
    {result}
    </content>
    </group_message>"""

    print(result)

    return result
    


embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=os.environ.get('dashscope_api_key')
    )


local_faiss_path = "./faiss_index_store"

vector_store = load_rag(embeddings, "./faiss_index_store")


async def retrieve_context(query: str):
    """
    加载专属知识库。

    Args:
        prompt: 用户的完整查询问题或意图描述
    Returns:
        格式化为 <rag_context> </rag_context>包裹的检索内容，供后续回答严格引用。"""
    
    # 加载嵌入模型

    if vector_store is None:
        return "知识库未加载"
    
    # 执行相似性搜索
    print(f"调用工具，加载_rag\n")
    raw_results = vector_store.similarity_search_with_score(query, k=7)

    score_threshold=0.38##归一化的相关性，小于0.38的都完全不相关
    results = [(doc, score) for doc, score in raw_results if score >= score_threshold]
    
    print(f"相似度最高的文档:\n")
    for i, (doc,score) in enumerate(results, 1):
        print(f"【文档 {i}】(相关度: {score:.4f})：{doc.page_content}\n")

    # 将结果合并为知识库文本
    knowledge_base = "\n\n".join([doc.page_content for doc,score in results])
    
    if not knowledge_base:
        print("暂无相关的文档")
    return f"""<rag_context>
    <source>rag_context</source>
    <content>
    {knowledge_base}
    </content>
    </rag_context>"""



class PromptInjectionError(Exception):
      """检测到提示词注入时抛出此异常"""
      pass


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
    

from typing import Any
@after_agent
def _testafter(state: AgentState,runtime: ToolRuntime[Context])->dict[str, Any] | None:
    a=1
    

from src.tools.load_skill import *
from src.tools.crawl import crawl_browser
agent = create_agent(
    model=llmmodel,
    system_prompt=PROMPT,
    tools=[user_at,load_luoke_skill,summarize,load_image,create_image,crawl_browser],##load_context
    ##get_group_messages
    context_schema=Context,
    middleware=[first_layer_security,_testafter],
)



from src.util.image_utils import replace_cq_codes_with_image_placeholder
from src.agents.checkagent import get_checkagent_simple
from src.config.llmconfig import basemodel

llm=on_command('/testllm')
@llm.handle()
async def _(bot: Bot, event: MessageEvent, message: Message = EventMessage()):

    '''
    m=str(message).replace("/testllm","")
    res=await get_checkagent_simple(basemodel,m)##获取审计agent来判断用户意图
    if res[0] is False:
        await llm.send(res[1])
        return '''

    group_id = event.group_id##获得当前用户的基本信息
    user_id=event.get_user_id()
    user_card=event.sender.card
    user_name=event.sender.nickname
    

    message=replace_cq_codes_with_image_placeholder(str(message))
    message=str(message).replace("/testllm","",1)## 删除输入的第一个/testllm 防止模型混淆
    rag_context=await retrieve_context(message)##召回rag
    
    memory=load_memory(group_id,user_id,user_name,user_card)##加载短期记忆
    msg=f"{rag_context}\n\n<<USER>>\n{message}\n<</USER>>\n\n\n{memory}"##拼接rag召回的内容和用户提示词


    if group_id is None:
          # 私聊情况，使用用户 ID 替代（避免工具报错）
          group_id = str(event.get_user_id())

    try:

        result=await agent.ainvoke(
            {"messages": [{"role": "user", "content": msg}]},
            context=Context(group_id=str(group_id),user_id=str(user_id),msg=msg,user_card=user_card,user_name=user_name,
                            bot=bot),
            config=DEFAULT_AGENT_CONFIG
        ) ## 执行智能体逻辑
        
        context = result["messages"][-1].content



        # 解析@标记并转换为真正的@消息
        ##final_message = await parse_at_mentions(bot, int(group_id), context)

        logger.info(f"\n输出的最终提示词【{context}】\n")

        text_part, img_list, is_succeed = await _process_pollinations_url(str(context))

        if is_succeed is False:
            await llm.send(Message("图片服务器连接超时了哦，请稍后再试"))
            return

        # 先切分文本（基于原始 text_part，避免 Message 对象干扰切分）
        segments = await split_message_for_human(text_part or "")
        if not segments:
            logger.warning("split_message_for_human returned empty, skipping send")
            return

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
        
        
        '''MINIMAX 兼容
        context = extract_reply(result["messages"][-1].content)
        # 解析@标记并转换为真正的@消息
        final_message = await parse_at_mentions(bot, int(group_id), context)

        await llm.send(final_message)
        '''
    except PromptInjectionError as e:
        # 捕获到提示词注入异常，直接返回错误消息
        logger.error(e)
        await llm.send(Message("检查到提示词注入异常,拒绝执行哦~"))
    except httpx.ReadTimeout:
        logger.error(f"⏱️ 图片生成超时，服务端响应太慢")
        await llm.send(Message("🖼️ 图片生成超时，先给你文字回复~"))
    except Exception as x:
        logger.exception(x)
        await llm.send(Message("发生未知异常呢~请联系管理员查看日志"))















from langchain.tools import tool
from langchain.agents import create_agent
from src.skills.skill.luokewangkuo import get_luoke_info
from src.skills.skill.summary_gruop_content import get_group_msg_skill
from src.config.llmconfig import basemodel

@tool
async def load_luoke_skill(query: str) -> str:
    """
    加载洛克王国的游戏规则与基本信息。

    使用场景：
        当用户询问洛克王国世界规则、洛克王国精灵对战规则，、洛克王国精灵属性克制必须调用此工具。

    Args:
        query: 用户的完整查询问题或意图描述

    Returns:
        格式化为 <skill> </skill>包裹的检索内容，供后续回答严格引用。
    """
    print('加载洛克王国skill')
    msg=get_luoke_info()

    msg=f"""<skill>
    <source>luoke_skill</source>
    <content>
    {msg}
    </content>
    </skill>/"""
    return msg


@tool
async def summarize(query:str)-> str:
    """
    总结群聊工具

    使用场景：
        当用户请求，总结群聊消息，总结一下群聊上下文的时候触发
        
    Args:
        query: 当前的群聊上下文，从<group_message> XML标签内获取完整的上下文信息,但是要去除XML标签只保留正文
            正文如下:
                【重要】当前用户信息（提问者）：
                - QQ号: XXXX
                - 用户名: XXXX
                - 群名片: XXXX

                【群聊历史记录】（仅供参考）：
                群 XXXXX 的最近 XXXXX 条消息：
                QQ号:XXXXX用户名:XXXX 群名片:XXXX
                message: XXXXX

                群 XXXXX 的最近 XXXXX 条消息：
                QQ号:XXXXX用户名:XXXX 群名片:XXXX
                message: XXXXX
                    
    Returns:
        1.严格返回总结内容
        2:当总结内容出现形如[本地图片路径]XXXXXXXX[/本地图片路径]时,你需要调用load_image传入图片路径,获取图片描述,严禁直接返回本地地址
       
    """
    print("调用工具summary")
    skill_rules=get_group_msg_skill()
    prompt = f'''你是一个专业的群聊总结助手。请严格遵循以下规则与步骤执行总结任务：
                {skill_rules}
                ⚠️ 输出要求：
                - 仅输出最终总结结果，禁止输出推理过程、中间步骤或额外解释
                - 若上下文为空、无意义或无法提取有效信息，直接返回：“暂无有效群聊内容可总结。”
                - 保持客观、结构化、语言简洁""")'''
             
    skill_agent = create_agent(
        model=basemodel,
        system_prompt=prompt,   
    )
    result=await skill_agent.ainvoke(
            {"messages": [{"role": "user", "content": query}]})
    print("聊天记录总结成功")
    
    return  result["messages"][-1].content
    
    

     
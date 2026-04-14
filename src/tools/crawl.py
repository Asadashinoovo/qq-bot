from langchain.tools import tool, ToolRuntime
from langchain.agents import create_agent
from src.config.llmconfig import basemodel
from src.skills.skill.summary_crawl_content import get_crawl_skill
from src.util.runtime import Context
import asyncio
from crawl4ai import *
from nonebot import logger

async def crawler(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)

        return result # 输出前300字符的Markdown


@tool
async def crawl_browser(query:str):
    '''
    读取网站tool

    触发方式：
        帮我看一下这个网站

    Args:
        网站的url,你需要从query中提取用户输入的网站url:
        例如:http:www.baidu.com,https://mp.weixin.qq.com,如果用户没加协议,比如www.baidu.com,你需要自行加上https
    Return:
        成功(SUCEESS):返回对网站信息的概括
        失败(ERROR_MESSAGE):直接返回总结错误的原因,不要描述这个网站
    '''

    url=query
    logger.info(f"开始爬取网站")
    try:
        result_container = await crawler(url)
        crawl_result = result_container[0]

        if not crawl_result.success:
           raise RuntimeError("由于特殊原因,无法获取这个网站中的内容哦，请联系管理员试试")
        content = crawl_result.markdown

        skill_rules = get_crawl_skill()
        prompt = f'''你是一个专业的网页内容总结助手。请严格遵循以下规则与步骤执行总结任务：
        {skill_rules}
        ⚠️ 输出要求：
        - 仅输出最终总结结果，禁止输出推理过程、中间步骤或额外解释
        - 若内容为空、无意义或无法提取有效信息，直接返回："暂无有效内容可总结。"
        - 保持客观、结构化、语言简洁'''

        skill_agent = create_agent(
            model=basemodel,
            system_prompt=prompt,
        )
        summary_result = await skill_agent.ainvoke(
            {"messages": [{"role": "user", "content": content}]})
        summary = summary_result["messages"][-1].content

        return f"SUCEESS:{summary}"


    except Exception as e:
        logger.error(f"爬取网站失败，错误信息为{e}")
        return "ERROR: 连接服务器超时哦，无法获取任何内容。"

from langchain.tools import tool
import os
from langchain.tools import tool, ToolRuntime
from src.util.runtime import Context
from src.config.longcat_client import LongCatClient
from src.config.pollinations_client import PollinationsImageClient
from src.util.image_utils import get_local_path
from src.util.image_utils import _local_image_to_base64
from src.security.encryption import decrypt_file_id
from nonebot import logger
@tool
async def load_image(query: str,runtime: ToolRuntime[Context]) -> str:
    """
    【触发条件】
        出现形如【当前图片】 【当前图片】调用此工具提取路径并分析图片。

    Args:
        query: 【当前图片】ASJFKHAIGHpng【当前图片】

    Returns:
        图片的详细结构化描述。若路径无效、权限不足或解析失败，返回明确的错误提示供 Agent 重试或降级。
    """

    try:
         
        bot=runtime.context.bot
        client = LongCatClient(os.environ.get('longcat_api'))  

        print(f"调用图片总结工具:加密后的图片为{query}")

        file_id =decrypt_file_id(query) 
        ##解码图片

        # 通过 bot API 获取本地路径（只读本地，不下载）
        local_path = await get_local_path(bot, file_id)

        b64 = _local_image_to_base64(local_path)

        description = await client.describe_image(
            image_base64=b64,
            prompt="请用中文简要描述这张图片"
        )
        print("调用图片总结完毕")
        return f"✅ 成功加载图片:描述如下{description}"
    
    except FileNotFoundError as e:
        return f"⚠️ 图片文件未找到: {str(e)}"
    except ValueError as e:
        return f"⚠️ 参数错误: {str(e)}"
    except Exception as e:
        return f"⚠️ 图片处理失败: {type(e).__name__}"
    



@tool
async def create_image(query: str,runtime: ToolRuntime[Context]) -> str:
    """
    【触发条件】
        出现形如给我生成一张图片,我想要一张XXXX的图片

    Args:
        query: 需要生成的图片的描述

    Returns:
        返回格式:
            成功： ###IMG###:{image_url}### 
            失败： XXX图片生成出现了一点小问题呢
        注意,如果成功，你必须且返回###IMG###:{image_url}###
        
    """
    print("调用图片生成tool")
    try:
        client = PollinationsImageClient()
        image_url = client.generate(prompt=query)
        logger.info(f"✅ 图片生成成功: {image_url}\n")
        return f"###IMG###:{image_url}###"
    except Exception as e:
        logger.error(f"❌ 图片生成异常: {type(e).__name__}: {e} 异常原因,图片llm服务器未能返回uri\n")
        return f"__IMG_ERROR__:{type(e).__name__}"
    



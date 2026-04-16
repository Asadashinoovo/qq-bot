import aiofiles
import base64
import os
from langchain.tools import tool, ToolRuntime
from src.util.runtime import Context
from src.config.longcat_client import LongCatClient
from src.config.pollinations_client import PollinationsImageClient
from src.util.image_utils import get_local_path
from src.security.encryption import decrypt_file_id
from nonebot import logger


# 模块级单例
_longcat_client = None


def get_longcat_client() -> LongCatClient:
    """获取 LongCatClient 单例，避免每次创建连接"""
    global _longcat_client
    if _longcat_client is None:
        _longcat_client = LongCatClient(os.environ.get('longcat_api'))
    return _longcat_client


async def _local_image_to_base64(local_path: str) -> str:
    """异步读取本地图片并转为 base64"""
    if local_path.startswith("file://"):
        from urllib.parse import urlparse
        local_path = urlparse(local_path).path
    async with aiofiles.open(local_path, 'rb') as f:
        data = await f.read()
    return base64.b64encode(data).decode('utf-8')


@tool
async def load_image(query: str, runtime: ToolRuntime[Context]) -> str:
    """
    【触发条件】
        出现形如【当前图片】 【当前图片】调用此工具提取路径并分析图片。

    Args:
        query: 【当前图片】ASJFKHAIGHpng【当前图片】

    Returns:
        图片的详细结构化描述。若路径无效、权限不足或解析失败，返回明确的错误提示供 Agent 重试或降级。
    """
    logger.info("[load_image] 开始调用图片总结功能")
    try:
        bot = runtime.context.bot
        client = get_longcat_client()
        file_id = decrypt_file_id(query)
        local_path = await get_local_path(bot, file_id)
        b64 = await _local_image_to_base64(local_path)
        description = await client.describe_image_async(
            image_base64=b64,
            prompt="请用中文简要描述这张图片"
        )
        logger.info(f"[load_image] API 调用成功，描述={description[:50]}")
        return f"✅ 成功加载图片:描述如下{description}"

    except FileNotFoundError as e:
        logger.error(f"[load_image] 文件未找到: {e}")
        return f"⚠️ 图片文件未找到: {str(e)}"
    except ValueError as e:
        logger.error(f"[load_image] 参数错误: {e}")
        return f"⚠️ 参数错误: {str(e)}"
    except Exception as e:
        logger.exception(f"[load_image] 未知异常: {e}")
        return f"⚠️ 图片处理失败: {type(e).__name__}"


@tool
async def create_image(query: str, runtime: ToolRuntime[Context]) -> str:
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
        image_url = await client.generate(prompt=query)
        logger.info(f"✅ 图片生成成功: {image_url}")
        return f"###IMG###:{image_url}###"
    except Exception as e:
        logger.error(f"❌ 图片生成异常: {type(e).__name__}: {e}")
        return f"__IMG_ERROR__:{type(e).__name__}"

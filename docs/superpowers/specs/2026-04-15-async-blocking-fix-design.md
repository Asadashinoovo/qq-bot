# 性能优化：消除异步上下文中的同步阻塞

## 背景

全面性能审查发现 `qqagentbot` 体系中存在 3 处同步阻塞代码在异步上下文中的问题，阻塞事件循环，影响并发性能。

## 问题清单

| # | 文件 | 问题 | 严重程度 |
|---|------|------|----------|
| 1 | `pollinations_client.py` | 同步 `requests.Session`，阻塞事件循环 | 高 |
| 2 | `load_image.py:37` | `_local_image_to_base64` 同步文件读取 | 中 |
| 3 | `load_image.py:27` | 每次创建新 `LongCatClient`，无连接复用 | 中 |

## 改造方案

### 1. `pollinations_client.py` — 替换为异步客户端

**改动**：删除同步 `requests` 实现，改用 `httpx.AsyncClient`。

```python
# pollinations_client.py
import httpx
import base64
from typing import Optional
from urllib.parse import quote

class PollinationsImageClient:
    BASE_URL = "https://image.pollinations.ai/prompt"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        *,
        model: str = "flux",
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        enhance: bool = False,
        nologo: bool = False,
    ) -> str:
        params = {
            "width": width,
            "height": height,
            "model": model,
            "enhance": str(enhance).lower(),
            "nologo": str(nologo).lower(),
        }
        if seed is not None:
            params["seed"] = seed

        encoded_prompt = quote(prompt, safe='')
        url = f"{self.BASE_URL}/{encoded_prompt}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, follow_redirects=True)
            return response.url
```

**行为变化**：
- `generate()` 从同步方法变为 `async generate()`
- 所有调用方必须 `await client.generate(...)`

### 2. `longcat_client.py` — 新增异步方法

**改动**：新增 `describe_image_async()`，原同步 `describe_image()` 保留（给其他模块使用）。

```python
# longcat_client.py 新增方法（原有方法不变）
async def describe_image_async(
    self,
    *,
    image_base64: str,
    prompt: str = "请详细描述这张图片的内容",
    timeout: int = 120
) -> str:
    """describe_image 的异步版本"""
    response = await self.client.chat.completions.create(
        model=self.model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "input_image", "input_image": {"type": "base64", "data": [image_base64]}},
                {"type": "text", "text": prompt}
            ]
        }],
        timeout=timeout
    )
    return response.choices[0].message.content.strip()
```

### 3. `load_image.py` — 单例 + 异步文件 + 异步 API

**改动**：
- `LongCatClient` 改为模块级单例
- `_local_image_to_base64` 改用 `aiofiles` 异步读取
- `load_image` 调用 `describe_image_async`
- `create_image` 调用 `PollinationsImageClient.generate`

```python
# load_image.py
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

def get_longcat_client():
    global _longcat_client
    if _longcat_client is None:
        _longcat_client = LongCatClient(os.environ.get('longcat_api'))
    return _longcat_client

async def _local_image_to_base64(local_path: str) -> str:
    if local_path.startswith("file://"):
        from urllib.parse import urlparse
        local_path = urlparse(local_path).path
    async with aiofiles.open(local_path, 'rb') as f:
        data = await f.read()
    return base64.b64encode(data).decode('utf-8')

@tool
async def load_image(query: str, runtime: ToolRuntime[Context]) -> str:
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
        return f"✅ 成功加载图片:描述如下{description}"
    except FileNotFoundError as e:
        return f"⚠️ 图片文件未找到: {str(e)}"
    except ValueError as e:
        return f"⚠️ 参数错误: {str(e)}"
    except Exception as e:
        return f"⚠️ 图片处理失败: {type(e).__name__}"

@tool
async def create_image(query: str, runtime: ToolRuntime[Context]) -> str:
    print("调用图片生成tool")
    try:
        client = PollinationsImageClient()
        image_url = await client.generate(prompt=query)
        logger.info(f"✅ 图片生成成功: {image_url}")
        return f"###IMG###:{image_url}###"
    except Exception as e:
        logger.error(f"❌ 图片生成异常: {type(e).__name__}: {e}")
        return f"__IMG_ERROR__:{type(e).__name__}"
```

### 4. `qqagentbot.py` — 调用方适配

**改动**：`create_image` 是 `@tool`，被 LangChain Agent 调用时已支持异步，无需改动。但需确保 import 路径正确。

## 依赖变更

| 依赖 | 变化 |
|------|------|
| `httpx` | 已有（用于 `_process_pollinations_url`），无需新增 |
| `aiofiles` | 新增，需 `pip install aiofiles` |

## 风险

| 风险 | 级别 | 缓解 |
|------|------|------|
| `aiofiles` 引入新依赖 | 低 | 纯 Python，兼容性好 |
| `httpx` 已有，无风险 | - | - |
| LongCat API OpenAI 兼容 | 低 | OpenAI SDK 5.x 原生支持异步 |

## 测试计划

1. `python -c "import src.config.pollinations_client; print('ok')"` — 验证 import
2. `python -c "import src.tools.load_image; print('ok')"` — 验证 import
3. `/testllm 请生成一张图片" — 集成测试 Pollinations 异步调用
4. `/testllm 请分析这张图片[CQ...]" — 集成测试图片加载异步流程
5. 常规 `/testllm` 对话回归测试

## 实施顺序

1. `longcat_client.py` — 新增 `describe_image_async`
2. `pollinations_client.py` — 替换为异步
3. `load_image.py` — 单例 + 异步文件 + 异步 API 调用
4. 添加 `aiofiles` 依赖
5. 测试验证

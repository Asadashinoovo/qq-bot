# 异步阻塞修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `pollinations_client.py`、`load_image.py` 中的同步阻塞代码改造为完全异步，消除事件循环阻塞。

**Architecture:** `PollinationsImageClient` 从同步 `requests` 改为 `httpx.AsyncClient`；`load_image.py` 的文件读取改用 `aiofiles`；`LongCatClient` 新增异步方法；所有客户端改为模块级单例复用。

**Tech Stack:** Python asyncio, httpx, aiofiles, OpenAI SDK async

---

## 文件变更概览

| 文件 | 改动类型 |
|------|----------|
| `src/config/longcat_client.py` | 修改 — 新增 `describe_image_async` |
| `src/config/pollinations_client.py` | 重写 — 同步改异步 |
| `src/tools/load_image.py` | 重写 — 单例 + 异步文件读取 |
| `pyproject.toml` | 修改 — 添加 `aiofiles` 依赖 |

---

## Task 1: 给 `longcat_client.py` 新增异步方法

**Files:**
- Modify: `src/config/longcat_client.py`

- [ ] **Step 1: 在 `longcat_client.py` 的 `LongCatClient` 类中添加 `describe_image_async` 方法**

在 `LongCatClient` 类的最后一个方法 `text_to_speech` 之后（仍在类内部），添加：

```python
    async def describe_image_async(
        self,
        *,
        image_base64: str,
        prompt: str = "请详细描述这张图片的内容",
        timeout: int = 120
    ) -> str:
        """
        describe_image 的异步版本。
        参数与同步版本完全一致，仅返回方式不同。
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "input_image": {
                            "type": "base64",
                            "data": [image_base64]
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }],
            timeout=timeout
        )
        return response.choices[0].message.content.strip()
```

- [ ] **Step 2: 验证语法正确**

```bash
cd "D:/Projects/mai-bot/mai-bot" && python -c "from src.config.longcat_client import LongCatClient; print('ok')"
```
Expected: `ok`（无输出或报错）

- [ ] **Step 3: 提交**

```bash
git add src/config/longcat_client.py && git commit -m "feat: add describe_image_async to LongCatClient"
```

---

## Task 2: 重写 `pollinations_client.py` 为异步客户端

**Files:**
- Modify: `src/config/pollinations_client.py`（全文重写）

- [ ] **Step 1: 备份并重写 `pollinations_client.py`**

将文件内容替换为：

```python
import httpx
from typing import Optional
from urllib.parse import quote


class PollinationsImageClient:
    """Pollinations.AI 图片生成客户端（异步版本）"""

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
        """
        生成图片（异步）。

        Args:
            prompt: 图片描述提示词
            model: 模型名称 (flux / turbo / stable-diffusion)
            width: 图片宽度
            height: 图片高度
            seed: 随机种子，不传则随机
            enhance: 是否让AI优化prompt
            nologo: 去水印（需认证）

        Returns:
            重定向后的最终图片 URL
        """
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

- [ ] **Step 2: 验证 import 不报错**

```bash
cd "D:/Projects/mai-bot/mai-bot" && python -c "from src.config.pollinations_client import PollinationsImageClient; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: 提交**

```bash
git add src/config/pollinations_client.py && git commit -m "refactor: rewrite PollinationsImageClient with async httpx"
```

---

## Task 3: 添加 `aiofiles` 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 在 `pyproject.toml` 的 dependencies 中添加 `aiofiles`**

找到 `[project.dependencies]` 或 `[tool.poetry.dependencies]` 部分，添加一行：

```toml
aiofiles = "*"
```

（或使用更具体的版本约束，如 `aiofiles = ">=23.0.0"`，参考现有依赖写法）

- [ ] **Step 2: 安装新依赖**

```bash
cd "D:/Projects/mai-bot/mai-bot" && uv pip install aiofiles
```

- [ ] **Step 3: 验证安装**

```bash
python -c "import aiofiles; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml uv.lock && git commit -m "chore: add aiofiles dependency"
```

---

## Task 4: 重写 `load_image.py`（单例 + 异步文件 + 异步 API）

**Files:**
- Modify: `src/tools/load_image.py`（全文重写）

- [ ] **Step 1: 重写 `load_image.py`**

将文件内容替换为：

```python
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
        print("调用图片总结完毕")
        return f"✅ 成功加载图片:描述如下{description}"

    except FileNotFoundError as e:
        return f"⚠️ 图片文件未找到: {str(e)}"
    except ValueError as e:
        return f"⚠️ 参数错误: {str(e)}"
    except Exception as e:
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
```

- [ ] **Step 2: 验证 import 不报错**

```bash
cd "D:/Projects/mai-bot/mai-bot" && python -c "from src.tools.load_image import load_image, create_image; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: 提交**

```bash
git add src/tools/load_image.py && git commit -m "refactor: rewrite load_image with async aiofiles and singleton"
```

---

## Task 5: 集成验证

**Files:**
- Test: 手动集成测试

- [ ] **Step 1: 验证 `qqagentbot.py` import 不受影响**

```bash
cd "D:/Projects/mai-bot/mai-bot" && python -c "from src.plugins import qqagentbot; print('ok')"
```
Expected: `ok`

- [ ] **Step 2: 确认所有工具可被 agent 正确加载**

启动机器人（后台），发送 `/testllm 你好` 验证基础流程未被破坏。

Expected: 正常回复，无报错

- [ ] **Step 3: 如有条件，测试图片生成和图片分析**

发送 `/testllm 请生成一张星空的图片` — 验证 Pollinations 异步调用正常。

---

## 实施顺序

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
```

每个 Task 独立可测试，完成后立即提交。

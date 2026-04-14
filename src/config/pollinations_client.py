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

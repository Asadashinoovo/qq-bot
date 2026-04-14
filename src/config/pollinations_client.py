# pollinations_client.py
import requests
import base64
from typing import Literal, Optional
from urllib.parse import quote

class PollinationsImageClient:
    """Pollinations.AI 图片生成客户端"""
    
    BASE_URL = "https://image.pollinations.ai/prompt"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        
    def generate(
        self,
        prompt: str,
        *,
        model: str = "flux",           # flux / turbo / stable-diffusion
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,    # 不传则随机
        enhance: bool = False,         # 是否让AI优化prompt
        nologo: bool = False,          # 去水印（需认证）
        return_type: Literal["url", "base64"] = "url",
        referrer: Optional[str] = None # 认证用
    ) -> str:
        """
        生成图片
        
        Args:
            prompt: 图片描述提示词
            return_type: "url" 返回图片链接 / "base64" 返回base64字符串
            
        Returns:
            图片URL 或 base64编码字符串（含data:image/jpeg;base64,前缀）
        """
        # 构建查询参数
        params = {
            "width": width,
            "height": height,
            "model": model,
            "enhance": str(enhance).lower(),
            "nologo": str(nologo).lower(),
        }
        if seed is not None:
            params["seed"] = seed
        if referrer:
            params["referrer"] = referrer
            
        # URL编码prompt，拼接请求地址
        encoded_prompt = quote(prompt, safe='')
        url = f"{self.BASE_URL}/{encoded_prompt}"
        
        try:
            if return_type == "url":
                # 直接返回URL（重定向后的最终地址）
                response = self.session.get(
                    url, params=params, timeout=self.timeout, allow_redirects=True
                )
                return response.url
                
            else:  # base64
                response = self.session.get(
                    url, params=params, timeout=self.timeout, allow_redirects=False
                )
                response.raise_for_status()
                # 编码为base64，添加MIME前缀方便前端直接使用
                b64 = base64.b64encode(response.content).decode('utf-8')
                return f"data:image/jpeg;base64,{b64}"
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"图片生成失败: {str(e)}")
    
    def get_models(self) -> list:
        """获取可用模型列表"""
        resp = self.session.get("https://image.pollinations.ai/models", timeout=10)
        return resp.json() if resp.ok else []
    
    def close(self):
        """关闭session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
# longcat_client.py
from openai import OpenAI
import os
import base64
import requests
import wave
from pathlib import Path
from typing import Optional, Union, Literal
import re


class LongCatClient:
    """长猫 API 客户端：支持图文理解 + 文本转语音"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.longcat.chat/openai/v1",
        model: str = "LongCat-Flash-Omni-2603",
        default_voice: str = "yangguangtianmei"
    ):
        self.api_key = api_key or os.environ.get('longcat_api')
        if not self.api_key:
            raise ValueError("请提供 api_key 或设置环境变量 longcat_api")
            
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        self.model = model
        self.default_voice = default_voice
    
    @staticmethod
    def _image_path_to_base64(image_path: str) -> str:
        """本地图片文件 → 纯base64字符串"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    @staticmethod
    def _image_url_to_base64(image_url: str, timeout: int = 30) -> str:
        """图片URL → 下载 → 纯base64字符串"""
        resp = requests.get(image_url, timeout=timeout)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode('utf-8')
    
    @staticmethod
    def _is_valid_base64(s: str) -> bool:
        """简单校验是否为合法base64字符串"""
        if not s or len(s) < 4:
            return False
        # 允许带或不带 MIME 前缀
        s_clean = re.sub(r'^data:image/\w+;base64,', '', s)
        try:
            base64.b64decode(s_clean, validate=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def _pcm_to_wav(pcm_path: str, wav_path: str, sample_rate: int = 24000):
        """PCM裸流 → 添加WAV文件头"""
        with open(pcm_path, 'rb') as f:
            pcm_data = f.read()
        with wave.open(wav_path, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit PCM
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_data)
    
    async def describe_image(
        self,
        *,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        prompt: str = "请详细描述这张图片的内容",
        timeout: int = 120
    ) -> str:
        """
        功能1：输入图片（三选一），输出文字描述
        
        Args:
            image_path: 本地图片文件路径（.jpg/.png等）
            image_url: 图片的公开访问URL
            image_base64: 纯base64字符串 或带data:preifx的base64
            prompt: 可选的提示词，默认请求详细描述
            timeout: 请求超时时间（秒）
            
        Returns:
            str: 模型返回的图片描述文本
            
        Raises:
            ValueError: 未提供图片或提供了多个图片源 / base64格式非法
            FileNotFoundError: image_path指定的文件不存在
            requests.RequestException: 下载image_url失败
        """
        # 🔍 参数校验：三选一
        sources = [image_path, image_url, image_base64]
        provided = sum(1 for s in sources if s is not None)
        
        if provided == 0:
            raise ValueError("必须提供 image_path / image_url / image_base64 其中之一")
        if provided > 1:
            raise ValueError("image_path / image_url / image_base64 只能提供一个")
        
        # 🔁 统一转换为纯base64字符串（不带data:前缀）
        if image_path:
            if not Path(image_path).exists():
                raise FileNotFoundError(f"图片不存在: {image_path}")
            b64_str = self._image_path_to_base64(image_path)
            
        elif image_url:
            b64_str = self._image_url_to_base64(image_url, timeout=timeout//2)
            
        else:  # image_base64
            # 清理可能的data:前缀
            b64_str = re.sub(r'^data:image/\w+;base64,', '', image_base64.strip())
            if not self._is_valid_base64(b64_str):
                raise ValueError("image_base64 格式不合法，请提供有效的base64编码")
        
        # 📤 调用API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "input_image": {
                            "type": "base64",
                            "data": [b64_str]  # ✅ 数组格式 + 纯base64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }],
            stream=False,
            timeout=timeout
        )
        return response.choices[0].message.content.strip()
    
    def text_to_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        speed: int = 50,
        volume: int = 50,
        sample_rate: int = 24000,
        return_base64: bool = True,
        timeout: int = 120
    ) -> dict:
        """
        功能2：输入文本，输出语音（base64 + 本地保存）
        
        Args:
            text: 要转换的文本内容
            output_path: 输出WAV文件路径，默认 "output.wav"
            voice: 音色名称，默认使用初始化时设置的
            speed: 语速 (0-100)
            volume: 音量 (0-100)
            sample_rate: 音频采样率
            return_base64: 是否在返回值中包含base64编码
            timeout: 请求超时时间
            
        Returns:
            dict: {
                "text": str,           # 模型返回的文本（如有）
                "audio_base64": str,   # 音频base64编码（如果return_base64=True）
                "saved_path": str      # 本地保存的WAV文件路径
            }
        """
        voice = voice or self.default_voice
        output_path = output_path or "output.wav"
        pcm_path = output_path.replace(".wav", ".pcm")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [{"type": "text", "text": f"请用语音回复：{text}"}]
            }],
            extra_body={
                "output_modalities": ["text", "audio"],
                "audio": {
                    "voice": voice,
                    "speed": speed,
                    "volume": volume,
                    "output_audio_samplerate": sample_rate
                }
            },
            stream=False,
            timeout=timeout
        )
        
        msg = response.choices[0].message
        audio_info = msg.audio
        
        # 处理音频数据
        if audio_info.type == "url":
            resp = requests.get(audio_info.data)
            resp.raise_for_status()
            with open(pcm_path, "wb") as f:
                f.write(resp.content)
        elif audio_info.type == "base64":
            audio_bytes = base64.b64decode(audio_info.data)
            with open(pcm_path, "wb") as f:
                f.write(audio_bytes)
        else:
            raise ValueError(f"未知的音频类型: {audio_info.type}")
        
        # PCM → WAV
        self._pcm_to_wav(pcm_path, output_path, sample_rate)
        
        # 清理临时文件
        if Path(pcm_path).exists():
            Path(pcm_path).unlink()
        
        # 构建返回值
        result = {
            "text": msg.content.strip() if msg.content else "",
            "saved_path": str(Path(output_path).resolve())
        }
        
        if return_base64:
            with open(output_path, "rb") as f:
                result["audio_base64"] = base64.b64encode(f.read()).decode('utf-8')
        
        return result
import os
import re
import base64
import asyncio
from src.security.encryption import encrypt_file_id
from src.security.encryption import decrypt_file_id
from pathlib import Path
import uuid
from nonebot import logger
import re, base64, asyncio, httpx

def _extract_file_id_from_cq(cq_query: str) -> str:
    """
    从 [CQ:image,...] 中提取 file 参数, 并且对参数进行加密
    示例: [CQ:image,summary=,file=ABC.png,...] → "ABC.png"
    """
    match = re.search(r'file=([^,\]]+)', cq_query)
    if not match:
        raise ValueError(f"未找到 file 参数: {cq_query}")
    
    return encrypt_file_id(match.group(1).strip())


def _local_image_to_base64(local_path: str) -> str:
    """读取本地图片文件转 base64（纯字符串）"""
    # 处理 file:// 协议（部分适配器返回）
    if local_path.startswith("file://"):
        from urllib.parse import urlparse
        local_path = urlparse(local_path).path
    
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"本地图片不存在: {local_path}")
    
    with open(local_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def get_local_path(bot, file_id: str) -> str:
    """
    调用 bot.call_api("get_image") 获取本地路径
    
    """
    res = await bot.call_api("get_image", file=file_id)
    return res.get("file", "")

  


CQ_PATTERN = re.compile(r'\[CQ:image,[^\]]+\]')


def replace_cq_codes_with_image_placeholder(message: str) -> str:
    """
    将 message 中的 [CQ:image,...] 替换为 【当前图片】fileID【当前图片】,并且把fileID采用AES-128-CBC加密

    示例输入: "/testllm 请分析[CQ:image,summary=,file=ABC.png,sub_type=0]"
    示例输出: "/testllm 请分析【当前图片】ABC.png【当前图片】"
    """
    def _replace_cq(cq_match: re.Match) -> str:
        cq_text = cq_match.group(0)
        try:
            file_id = _extract_file_id_from_cq(cq_text)
            return f"【当前图片】{file_id}【当前图片】"
        except ValueError:
            # 如果提取失败，保留原文本
            return cq_text

    return CQ_PATTERN.sub(_replace_cq, message)


async def _process_pollinations_url(text: str) -> tuple[str, list[str],bool]:
    """
    把msg中的###IMG###:https://imux&enhance=false&nologo=false###或者https://imux&enhance=false&nologo=false
    原始格式转换成本地path然后拼接到msg中
    """
    pattern = r'(?:###IMG###:)?(https://image\.pollinations\.ai/[^\s#]+)(?:###)?'
    urls = re.findall(pattern, text)
    urls = [m[0] if isinstance(m, tuple) else m for m in urls]
    if not urls:
        return text, [],True
    
    # 删带标记的URL
    text_clean = re.sub(r'###IMG###:[^\s]+###', '', text).strip()
    
    # 删纯 URL
    text_clean = re.sub(r'https://image\.pollinations\.ai/[^\s#]+', '', text_clean).strip()
    text_clean = re.sub(r'\[.*?\]\(\s*\)|\[\s*\]\(\s*\)', '', text_clean).strip()
    text_clean = re.sub(r'\s{2,}', ' ', text_clean).strip()

    project_root = Path(__file__).resolve().parents[2]  # 根据你的实际结构调整
    tmp_dir = project_root / "tmp" / "pollinations_imgs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    async def _fetch_and_save(url: str):##从图片服务器下载到本地
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
                
            # 生成唯一文件名：时间戳+uuid，避免冲突
            filename = f"{int(asyncio.get_event_loop().time())}_{uuid.uuid4().hex[:8]}.jpg"
            file_path = tmp_dir / filename
                
            # 写入文件（同步写，因为内容是内存中的，开销很小）
            with open(file_path, 'wb') as f:
                f.write(resp.content)
            logger.debug(f"✅ 下载成功: {url} → {file_path}")
            return str(file_path.resolve())  # 返回绝对路径字符串
       
    
    # 并行下载所有图片,收集错误数据
    results = await asyncio.gather(*[_fetch_and_save(u) for u in urls], return_exceptions=True)
    
    # 过滤出成功下载的路径（str 且非空）
    valid = []
    all_success = True

    ##打印收集到的数据
    for i, (u, r) in enumerate(zip(urls, results), 1):
        if isinstance(r, Exception):
            # 调用者通过 ERROR 日志感知具体哪个 URL 失败
            logger.error(f"❌ [{i}/{len(urls)}] {u[:80]}... 下载失败: {type(r).__name__}: {r}")
            all_success = False 
        elif isinstance(r, str) and r:
            valid.append(r)
            logger.info(f"✅ [{i}/{len(urls)}] {u[:80]}... → {r}")
        else:
            logger.warning(f"⚠️  [{i}/{len(urls)}] {u[:80]}... 未知结果: {r}")
            all_success = False
    
    # 汇总日志
    logger.info(f"📊 下载汇总: {len(urls)} 个 URL → 成功 {len(valid)} 个, 失败 {len(urls)-len(valid)} 个")
    

    return text_clean, valid,all_success

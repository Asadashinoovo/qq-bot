# main.py
from longcat_client import LongCatClient
import os
import base64
# 1️⃣ 初始化客户端

client = LongCatClient(os.environ.get('longcat_api'))  # 或从环境变量读取

# 2️⃣ 功能1：图片描述
image_path="C:/Users/17712/Desktop/QQ_1775828027156.png"
with open(image_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

description = client.describe_image(
    ##image_path="C:/Users/17712/Desktop/QQ_1775828027156.png",
    image_base64=b64,
    prompt="请用中文简要描述这张图片"
)
print(f"🖼️ 图片描述: {description}")

'''
# 3️⃣ 功能2：文本转语音 + 获取base64
result = client.text_to_speech(
    text="你好，我是长猫助手，很高兴为你服务",
    output_path="greeting.wav",  # 自定义输出路径
    voice="yangguangtianmei",    # 可选音色
    speed=60,                     # 稍快语速
    return_base64=True           # 返回base64编码
)

print(f"📝 回复文本: {result['text']}")
print(f"💾 保存路径: {result['saved_path']}")
print(f"🔐 Base64前50字符: {result['audio_base64'][:50]}...")
'''

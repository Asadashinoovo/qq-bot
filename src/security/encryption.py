"""
安全模块：图片ID加密解密
基于 Fernet (AES-128-CBC + HMAC)，开源主流算法
"""
import os
import base64
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# 私钥（生产环境应从环境变量或配置文件读取）
_private_key = os.environ.get('security_key')
_salt = os.environ.get('security_salt')  # 生产环境应从环境变量读取独立的 salt
_salt = _salt.encode('utf-8')

def _derive_key(key: str) -> bytes:
    """从私钥派生 Fernet 密钥"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(key.encode()))


_fernet = Fernet(_derive_key(_private_key))


def encrypt_file_id(file_id: str) -> str:
    """
    加密 file ID，返回 URL 安全的 base64 字符串
    """
    return _fernet.encrypt(file_id.encode("utf-8")).decode("ascii")


def decrypt_file_id(encrypted_id: str) -> str:
    """
    解密 encrypted_id，返回原始 file ID
    """
    return _fernet.decrypt(encrypted_id.encode("ascii")).decode("utf-8")


def generate_random_id(length: int = 16) -> str:
    """生成随机安全ID"""
    return secrets.token_urlsafe(length)[:length]

"""Skills 包 - 自动加载所有技能"""

from .loader import _loader
_loader.load_all()

__all__ = ['load_skills']

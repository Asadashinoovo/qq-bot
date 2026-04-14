"""自动扫描并加载 skills/skill 目录下的所有技能"""

from pathlib import Path
from typing import Dict
import importlib.util
from .registry import SkillRegistry, SkillEntry


class SkillAutoLoader:
    """自动加载技能"""

    def __init__(self, skills_dir: str = "src/skills/skill"):
        self.skills_dir = Path(skills_dir)
        self._loaded = False

    def load_all(self) -> Dict[str, SkillEntry]:
        """扫描并加载所有 skill.py 文件

        Returns:
            加载的技能字典
        """
        if self._loaded:
            return SkillRegistry()._skills

        registry = SkillRegistry()

        for py_file in self.skills_dir.glob("*.py"):
            # 跳过 __init__.py
            if py_file.name.startswith("_"):
                continue

            try:
                module_name = py_file.stem
                module_path = f"src.skills.skill.{module_name}"

                # 动态导入模块
                module = importlib.import_module(module_path)

                # 检查是否有必要的属性
                if not hasattr(module, 'SKILL_ID') or not hasattr(module, 'PROCESS'):
                    print(f"跳过 {module_name}：缺少必要属性 SKILL_ID 或 PROCESS")
                    continue

                # 注册技能
                registry.register(SkillEntry(
                    skill_id=getattr(module, 'SKILL_ID'),
                    name=getattr(module, 'NAME', module.SKILL_ID),
                    keywords=getattr(module, 'KEYWORDS', []),
                    process=getattr(module, 'PROCESS', "")
                ))
                print(f"已加载技能: {module.SKILL_ID} - {getattr(module, 'NAME', module.SKILL_ID)}")

            except Exception as e:
                print(f"加载 {py_file.name} 失败: {e}")

        self._loaded = True
        return registry._skills


# 全局加载器实例
_loader = SkillAutoLoader()


def load_skills() -> None:
    """触发加载所有技能"""
    _loader.load_all()

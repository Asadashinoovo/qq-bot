"""技能注册中心 - 管理所有技能的注册、查询和搜索"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SkillEntry:
    """技能条目"""
    skill_id: str              # 唯一标识
    name: str                  # 显示名称
    keywords: List[str]        # 匹配关键词
    process: str               # 流程规范（真正注入给 agent 的内容）


class SkillRegistry:
    """全局技能注册中心（单例模式）"""

    _instance: Optional['SkillRegistry'] = None
    _skills: Dict[str, SkillEntry] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, skill: SkillEntry) -> None:
        """注册技能"""
        self._skills[skill.skill_id] = skill

    def search(self, keywords: List[str]) -> List[SkillEntry]:
        """根据关键词搜索匹配的技能

        Args:
            keywords: 关键词列表

        Returns:
            匹配的技能列表
        """
        results = []
        keywords = [k.lower().strip() for k in keywords if k.strip()]

        for skill in self._skills.values():
            # 检查 skill 的 keywords 是否包含任一用户关键词
            match = any(
                any(kw in skill_keyword.lower() for kw in keywords)
                for skill_keyword in skill.keywords
            )
            if match:
                results.append(skill)

        return results

    def get_all_metas(self) -> List[Dict]:
        """获取所有技能的元数据

        Returns:
            技能元数据列表
        """
        return [
            {
                "id": s.skill_id,
                "name": s.name,
                "keywords": s.keywords
            }
            for s in self._skills.values()
        ]

    def list_all(self) -> str:
        """列出所有技能的详细信息

        Returns:
            格式化的技能列表字符串
        """
        if not self._skills:
            return "暂无可用技能"

        lines = ["=== 可用技能列表 ==="]
        for skill in self._skills.values():
            lines.append(f"\n【{skill.name}】(ID: {skill.skill_id})")
            lines.append(f"  匹配词: {', '.join(skill.keywords)}")
        return "\n".join(lines)

    def clear(self) -> None:
        """清空所有注册的技能（主要用于测试）"""
        self._skills.clear()

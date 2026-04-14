from dataclasses import dataclass
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot


@dataclass
class Context:
    group_id: str
    user_id: str
    user_name: str
    user_card :str
    msg :str
    bot :Bot
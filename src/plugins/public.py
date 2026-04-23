from nonebot import on_command, on_notice, get_driver
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment, GroupMessageEvent
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from src.libraries.image import *
from collections import deque
from nonebot.rule import to_me
import re
import csv
from pathlib import Path
from nonebot_plugin_userinfo import get_user_info
from nonebot.params import EventMessage



exportfile = on_command('/export')
@exportfile.handle()
async def ex(bot: Bot, event: Event):
    logger = get_driver().logger
    logger.info("导出命令被触发")

    # 检查是否在群聊中
    if not isinstance(event, GroupMessageEvent):
        await bot.send(event, "此命令只能在群聊中使用")
        return

    group_id = event.group_id
    logger.info(f"群号: {group_id}")

    try:
        # 获取群成员列表
        member_list = await bot.get_group_member_list(group_id=group_id)
        logger.info(f"获取到 {len(member_list)} 个成员")

        if not member_list:
            await bot.send(event, "无法获取群成员列表")
            return

        # 创建 tmp 目录（如果不存在）
        tmp_dir = Path("tmp")
        tmp_dir.mkdir(exist_ok=True)

        # 创建 CSV 文件名
        csv_filename = tmp_dir / f"group_{group_id}_members.csv"
        logger.info(f"文件路径: {csv_filename}")

        # 写入 CSV 文件
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['QQ号', '昵称', '群名片', '性别', '群头衔', '入群时间', '最后发言时间']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for member in member_list:
                writer.writerow({
                    'QQ号': member.get('user_id', ''),
                    '昵称': member.get('nickname', ''),
                    '群名片': member.get('card', '') or member.get('nickname', ''),
                    '性别': member.get('sex', ''),
                    '群头衔': member.get('title', ''),
                    '入群时间': member.get('join_time', ''),
                    '最后发言时间': member.get('last_sent_time', '')
                })

        logger.info("导出成功，准备发送消息")
        await bot.send(event, "导出成功")

    except Exception as e:
        logger.error(f"导出异常: {e}", exc_info=True)
        await bot.send(event, f"导出失败: {str(e)}")






exportfileV2 = on_command('/eexport')
@exportfileV2.handle()
async def ex(bot: Bot, event: Event):
    logger = get_driver().logger
    logger.info("导出命令被触发")

    

    group_id = 839276724
    logger.info(f"群号: {group_id}")

    try:
        # 获取群成员列表
        member_list = await bot.get_group_member_list(group_id=group_id)
        logger.info(f"获取到 {len(member_list)} 个成员")

        if not member_list:
            await bot.send(event, "无法获取群成员列表")
            return

        # 创建 tmp 目录（如果不存在）
        tmp_dir = Path("tmp")
        tmp_dir.mkdir(exist_ok=True)

        # 创建 CSV 文件名
        csv_filename = tmp_dir / f"group_{group_id}_members.csv"
        logger.info(f"文件路径: {csv_filename}")

        # 写入 CSV 文件
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['QQ号', '昵称', '群名片', '性别', '群头衔', '入群时间', '最后发言时间']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for member in member_list:
                writer.writerow({
                    'QQ号': member.get('user_id', ''),
                    '昵称': member.get('nickname', ''),
                    '群名片': member.get('card', '') or member.get('nickname', ''),
                    '性别': member.get('sex', ''),
                    '群头衔': member.get('title', ''),
                    '入群时间': member.get('join_time', ''),
                    '最后发言时间': member.get('last_sent_time', '')
                })

        logger.info("导出成功，准备发送消息")
        ##await bot.send(event, "导出成功")

    except Exception as e:
        logger.error(f"导出异常: {e}", exc_info=True)
        ##await bot.send(event, f"导出失败: {str(e)}")


help = on_command('/help')
@help.handle()
async def _(bot: Bot, event: Event, state: T_State):
    help_str = '''可用命令如下：
今日舞萌 查看今天的舞萌运势
XXXmaimaiXXX什么 随机一首歌
随个[dx/标准][绿黄红紫白]<难度> 随机一首指定条件的乐曲
查歌<乐曲标题的一部分> 查询符合条件的乐曲
[绿黄红紫白]id<歌曲编号> 查询乐曲信息或谱面信息
<歌曲别名>是什么歌 查询乐曲别名对应的乐曲
定数查歌 <定数>  查询定数对应的乐曲
定数查歌 <定数下限> <定数上限>
分数线 <难度+歌曲id> <分数线> 详情请输入“分数线 帮助”查看'''
    await help.send(help_str)

'''
at_user = on_command('/@')
@at_user.handle()
async def _(bot: Bot, event: Event, state: T_State):
    args = str(state.get("_prefix", {}).get("command_arg", "")).strip()
    if not args:
        await at_user.send("请输入QQ号，例如：/@ 1771264546")
        return

    try:
        user_id = int(args)
    except ValueError:
        await at_user.send("QQ号格式错误")
        return

    await at_user.send(MessageSegment.at(user_id))
'''

async def _group_poke(bot: Bot, event: Event) -> bool:
    value = (event.notice_type == "notify" and event.sub_type == "poke" and event.target_id == int(bot.self_id))
    return value


poke = on_notice(rule=_group_poke, priority=10, block=True)


@poke.handle()
async def _(bot: Bot, event: Event, state: T_State):
    if event.__getattribute__('group_id') is None:
        event.__delattr__('group_id')
    await poke.send(Message([
        MessageSegment("poke",  {
           "qq": f"{event.sender_id}"
       })
    ]))


# 群消息历史记录，按群ID分类，每个群最多保留100条
group_message_history: dict[int, deque] = {}


from src.util.image_utils import replace_cq_codes_with_image_placeholder

@event_preprocessor
async def preprocessor(bot:Bot, event: Event):
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        user_id=event.get_user_id()

        message=event.message

      
        message=replace_cq_codes_with_image_placeholder(str(message))
        
        
        if group_id not in group_message_history:
            group_message_history[group_id] = deque(maxlen=100)
        group_message_history[group_id].append({
            "user_id": user_id,
            "user_name": event.sender.nickname,
            "user_card": event.sender.card,
            "message": message,
            "message_id": event.message_id,
            "time": event.time
        })
    if hasattr(event, 'message_type') and event.message_type == "private" and event.sub_type != "friend":
        raise IgnoredException("not reply group temp message")



get = on_command('/get')
@get.handle()
async def getinfo(bot: Bot, event: Event, state: T_State):
    args = str(state.get("_prefix", {}).get("command_arg", "")).strip()
    if not args:
        await get.send("请输入群号，例如：/get 123456789")
        return

    try:
        group_id = int(args)
    except ValueError:
        await get.send("群号格式错误")
        return

    history = group_message_history.get(group_id)
    if not history:
        await get.send(f"群 {group_id} 暂无消息记录")
        return

    result = [f"群 {group_id} 的最近 {len(history)} 条消息："]
    for i, msg in enumerate(history, 1):
        result.append(f"{i}. [{msg['user_name']}]: {msg['message']}")
    await get.send("\n".join(result))

def record_bot_msg(group_id: int, msg_str: str, bot: Bot,time):
      if group_id not in group_message_history:
          group_message_history[group_id] = deque(maxlen=100)
      group_message_history[group_id].append({
          "user_id": str(bot.self_id),
          "user_name": "",
          "user_card": "",
          "message": msg_str,
          "message_id": None,
          "time": time
      })


async def parse_at_mentions(bot: Bot, group_id: int, text: str) -> Message:
    """
    解析文本中的@标记，转换为真正的@消息段。

    只支持格式: @QQ号（纯数字）
    如果格式错误（非纯数字），返回错误信息。

    Args:
        bot: Bot实例
        group_id: 群号
        text: 包含@标记的文本

    Returns:
        解析后的Message对象，包含真正的@消息段或错误信息
    """
    # 匹配@QQ号格式（纯数字）
    qq_pattern = r'@(\d+)'
    qq_matches = list(re.finditer(qq_pattern, text))

    if not qq_matches:
        return Message(text)

    # 处理纯数字QQ号格式
    result_parts = []
    last_end = 0

    for match in qq_matches:
        result_parts.append(text[last_end:match.start()])
        qq_num = match.group(1)
        result_parts.append(MessageSegment.at(int(qq_num)))
        last_end = match.end()

    result_parts.append(text[last_end:])
    return Message(result_parts)



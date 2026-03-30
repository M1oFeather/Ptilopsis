# -*- encoding:utf-8 -*-

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .adapter import BaseAdapter

class BaseEvent:
    """所有事件的基类，实现Mod式事件的核心能力"""
    event_name: str
    is_cancelled: bool = False

    def __init__(self):
        self.event_name = self.__class__.__name__

    def cancel(self) -> None:
        """取消事件，低优先级监听器将不再执行"""
        self.is_cancelled = True

class MessageEvent(BaseEvent):
    """通用消息事件，覆盖私聊、群聊，所有平台通用"""
    def __init__(
        self,
        adapter: BaseAdapter,
        sender_id: str,
        target_id: str,
        content: str,
        is_group: bool = False
    ):
        super().__init__()
        self.adapter = adapter  # 来源适配器
        self.sender_id = sender_id  # 发送者ID
        self.target_id = target_id  # 目标ID（群号/私聊ID）
        self.content = content  # 消息内容
        self.is_group = is_group  # 是否群消息

    async def reply(self, content: str) -> None:
        """统一回复接口，插件无需关心平台"""
        await self.adapter.send_message(self.target_id, content)
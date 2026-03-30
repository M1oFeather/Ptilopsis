from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .adapter import BaseAdapter

class BaseEvent:
    """所有事件的基类，实现Mod式事件的核心能力"""
    event_name: str
    is_cancelled: bool = False
    # 新增：传播阻断标记
    is_propagation_stopped: bool = False

    def __init__(self):
        self.event_name = self.__class__.__name__

    def cancel(self) -> None:
        """取消事件，后续不忽略取消的监听器将跳过执行"""
        self.is_cancelled = True

    # 新增：阻断事件传播方法
    def stop_propagation(self) -> None:
        """阻断事件传播，后续所有阶段、所有监听器一律终止执行"""
        self.is_propagation_stopped = True

class MessageEvent(BaseEvent):
    """通用消息事件，所有平台统一标准"""
    def __init__(
        self,
        adapter: BaseAdapter,
        sender_id: str,
        target_id: str,
        content: str,
        is_group: bool = False
    ):
        super().__init__()
        self.adapter = adapter
        self.sender_id = sender_id
        self.target_id = target_id
        self.content = content
        self.is_group = is_group

    async def reply(self, content: str) -> None:
        """统一回复接口，无需关心平台差异"""
        await self.adapter.send_message(self.target_id, content)
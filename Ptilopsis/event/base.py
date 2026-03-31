# -*- encoding:utf-8 -*-
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..adapter.base import BaseAdapter

class BaseEvent:
    event_name: str
    is_cancelled: bool = False
    is_propagation_stopped: bool = False

    def __init__(self):
        self.event_name = self.__class__.__name__

    def cancel(self) -> None:
        self.is_cancelled = True

    def stop_propagation(self) -> None:
        self.is_propagation_stopped = True

class MessageEvent(BaseEvent):
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
        await self.adapter.send_message(self.target_id, content)
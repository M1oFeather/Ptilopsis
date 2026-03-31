# Ptilopsis/adapter/console_adapter.py
import asyncio
from .base import BaseAdapter
from Ptilopsis.event.base import MessageEvent

class ConsoleAdapter(BaseAdapter):
    adapter_id = "console"
    platform = "控制台"

    def __init__(self, core, config=None):
        super().__init__(core, config or {})
        self._running = False

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._listen_input())

    async def stop(self) -> None:
        self._running = False

    async def send_message(self, target: str, content: str) -> None:
        print(f"[Bot -> {target}]: {content}")

    async def _listen_input(self) -> None:
        """监听控制台输入，模拟平台消息"""
        while self._running:
            try:
                content = await asyncio.to_thread(input, "[输入消息]: ")
                # 转换为标准事件，发布到事件总线
                event = MessageEvent(
                    adapter=self,
                    sender_id="console_user",
                    target_id="console",
                    content=content,
                    is_group=False
                )
                await self.core.event_bus.publish(event)
            except (EOFError, KeyboardInterrupt):
                break
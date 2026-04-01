# Ptilopsis/adapter/console_adapter.py
import asyncio
import sys
from typing import Dict, Any, Optional, List, Union
from .base import BaseAdapter
from ..event.base import (
    MessageEvent, MessageScene, MessageSegment,
    HeartbeatEvent
)

class ConsoleAdapter(BaseAdapter):
    """
    控制台适配器，用于本地调试与测试
    完全适配新架构规范，模拟私聊/群聊双场景
    """
    adapter_id = "console"
    platform = "console"

    def __init__(self, core, config: Dict[str, Any] = None):
        super().__init__(core, config)
        self.default_scene = self.config.get("default_scene", "group")
        self.mock_user_id = self.config.get("mock_user_id", "10001")
        self.mock_group_id = self.config.get("mock_group_id", "10000")
        self.mock_nickname = self.config.get("mock_nickname", "博士")
        self._running: bool = False
        self._input_task: Optional[asyncio.Task] = None
        self._mock_message_id = 0
        self._mock_friend_list = [{"user_id": self.mock_user_id, "nickname": self.mock_nickname}]
        self._mock_group_list = [{"group_id": self.mock_group_id, "group_name": "罗德岛指挥中心"}]
        self._mock_group_member = [{"user_id": self.mock_user_id, "nickname": self.mock_nickname, "role": "owner"}]

    async def start(self) -> None:
        self._running = True
        print(f"[控制台适配器] 启动成功，默认场景：{self.default_scene}")
        print("[输入消息]: ", end="", flush=True)
        self._input_task = asyncio.create_task(self._input_loop())
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        self._running = False
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()
        print(f"\n[控制台适配器] 已停止")

    async def _input_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                content = await loop.run_in_executor(None, sys.stdin.readline)
                content = content.strip()
                if not content:
                    print("[输入消息]: ", end="", flush=True)
                    continue

                self._mock_message_id += 1
                message_id = str(self._mock_message_id)

                # 【核心修复】：直接使用 MessageEvent 而非子类，以通过 EventBus 的严格类匹配
                scene_type = MessageScene.PRIVATE if self.default_scene == "private" else MessageScene.GROUP
                group_id_val = self.mock_group_id if scene_type == MessageScene.GROUP else None

                event = MessageEvent(
                    adapter=self,
                    raw_event={"content": content},
                    scene=scene_type,
                    message_id=message_id,
                    user_id=self.mock_user_id,
                    group_id=group_id_val,
                    content=content,
                    message=[MessageSegment.text(content)],
                    raw_message=content,
                    sender={"user_id": self.mock_user_id, "nickname": self.mock_nickname, "role": "owner"}
                )

                await self._publish_event(event)
                # 给一点微小的延迟，确保插件的 print 输出完毕后再打印下一行的提示符
                await asyncio.sleep(0.05)
                print("[输入消息]: ", end="", flush=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n[控制台适配器] 输入处理错误: {e}")
                print("[输入消息]: ", end="", flush=True)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(5)
            if self._running:
                event = HeartbeatEvent(self, {}, 5000)
                await self._publish_event(event)

    async def send_message(self, scene: str, target_id: str, message: Union[str, List[MessageSegment]], **kwargs) -> str:
        if isinstance(message, str):
            content = message
        else:
            content_parts = []
            for seg in message:
                if seg.type == "text":
                    content_parts.append(seg.data.get("text", ""))
                elif seg.type == "at":
                    content_parts.append(f"@{seg.data.get('qq', seg.data.get('user_id', ''))}")
                elif seg.type == "image":
                    content_parts.append(f"[图片: {seg.data.get('file', '')}]")
                else:
                    content_parts.append(f"[{seg.type}]")
            content = "".join(content_parts)

        scene_name = "私聊" if scene == "private" else "群聊"
        print(f"\n[白面鸮 {scene_name}]: {content}")
        self._mock_message_id += 1
        return str(self._mock_message_id)

    # ... [其他不需要修改的基类方法实现：delete_message, get_user_info 等保持原逻辑即可] ...
    async def delete_message(self, message_id: str) -> None: pass
    async def get_message(self, message_id: str) -> Dict[str, Any]: return {}
    async def get_user_info(self, user_id: str, no_cache: bool = False) -> Dict[str, Any]: return {}
    async def get_friend_list(self) -> List[Dict[str, Any]]: return []
    async def get_group_info(self, group_id: str, no_cache: bool = False) -> Dict[str, Any]: return {}
    async def get_group_list(self) -> List[Dict[str, Any]]: return []
    async def get_group_member_info(self, group_id: str, user_id: str, no_cache: bool = False) -> Dict[str, Any]: return {}
    async def get_group_member_list(self, group_id: str) -> List[Dict[str, Any]]: return []
    async def set_group_kick(self, group_id: str, user_id: str, reject_add_request: bool = False) -> None: pass
    async def set_group_ban(self, group_id: str, user_id: str, duration: int = 0) -> None: pass
    async def set_group_whole_ban(self, group_id: str, enable: bool = True) -> None: pass
    async def set_group_admin(self, group_id: str, user_id: str, enable: bool = True) -> None: pass
    async def handle_friend_request(self, flag: str, approve: bool = True, remark: str = "", **kwargs) -> None: pass
    async def handle_group_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "", **kwargs) -> None: pass
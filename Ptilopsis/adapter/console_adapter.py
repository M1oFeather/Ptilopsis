# Ptilopsis/adapter/console_adapter.py
import asyncio
import sys
from typing import Dict, Any, Optional, List, Union
from .base import BaseAdapter
from ..event.base import (
    MessageEvent, MessageScene, MessageSegment,
    HeartbeatEvent,
    GroupRecallEvent, FriendRecallEvent, GroupAdminEvent,
    GroupUploadEvent, FriendAddEvent, PokeEvent
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
        
        # 检查是否在交互式环境中运行
        if sys.stdin.isatty():
            print("[输入消息]: ", end="", flush=True)
            self._input_task = asyncio.create_task(self._input_loop())
        else:
            print("[控制台适配器] 非交互式环境，跳过输入循环")
            print("[提示] 可以通过API调用与控制台适配器交互")
        
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        self._running = False
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()
        print(f"\n[控制台适配器] 已停止")

    async def _input_loop(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            # 尝试读取一行来测试stdin是否可用
            test_content = await loop.run_in_executor(None, sys.stdin.readline)
        except Exception:
            # stdin 不可用，退出输入循环
            print("\n[控制台适配器] 标准输入不可用，退出输入循环")
            return
        
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
                print("[控制台适配器] 标准输入异常，退出输入循环")
                break

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
                    content_parts.append(f"[图片: {seg.data.get('file', seg.data.get('url', ''))}]")
                elif seg.type == "face":
                    content_parts.append(f"[表情:{seg.data.get('id', '')}]")
                elif seg.type == "record":
                    content_parts.append(f"[语音: {seg.data.get('file', seg.data.get('url', ''))}]")
                elif seg.type == "video":
                    content_parts.append(f"[视频: {seg.data.get('file', seg.data.get('url', ''))}]")
                elif seg.type == "reply":
                    content_parts.append(f"[回复:{seg.data.get('id', '')}]")
                elif seg.type == "share":
                    content_parts.append(f"[分享: {seg.data.get('title', '')} - {seg.data.get('url', '')}]")
                elif seg.type == "music":
                    content_parts.append(f"[音乐: {seg.data.get('title', '')}]")
                elif seg.type == "forward":
                    content_parts.append(f"[合并转发消息]")
                elif seg.type == "xml":
                    content_parts.append(f"[XML消息]")
                elif seg.type == "json":
                    content_parts.append(f"[JSON消息]")
                elif seg.type == "poke":
                    content_parts.append(f"[戳一戳@{seg.data.get('qq', '')}]")
                elif seg.type == "markdown":
                    content_parts.append(f"[Markdown: {seg.data.get('content', '')}]")
                else:
                    content_parts.append(f"[{seg.type}]")
            content = "".join(content_parts)

        scene_name = "私聊" if scene == "private" else "群聊"
        print(f"\n[白面鸮 {scene_name}]: {content}")
        self._mock_message_id += 1
        return str(self._mock_message_id)

    # ... [其他不需要修改的基类方法实现：delete_message, get_user_info 等保持原逻辑即可] ...
    async def delete_message(self, message_id: str) -> None:
        print(f"[控制台适配器] 撤回消息: {message_id}")

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        return {
            "message_id": message_id,
            "content": "[控制台消息]",
            "sender": {"user_id": self.mock_user_id, "nickname": self.mock_nickname}
        }

    async def get_user_info(self, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        return {"user_id": user_id, "nickname": f"用户{user_id}", "age": 0, "sex": "unknown"}

    async def get_friend_list(self) -> List[Dict[str, Any]]:
        return self._mock_friend_list

    async def get_group_info(self, group_id: str, no_cache: bool = False) -> Dict[str, Any]:
        return {"group_id": group_id, "group_name": "罗德岛指挥中心", "member_count": 1}

    async def get_group_list(self) -> List[Dict[str, Any]]:
        return self._mock_group_list

    async def get_group_member_info(self, group_id: str, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "nickname": self.mock_nickname,
            "card": "",
            "role": "owner"
        }

    async def get_group_member_list(self, group_id: str) -> List[Dict[str, Any]]:
        return self._mock_group_member

    async def set_group_kick(self, group_id: str, user_id: str, reject_add_request: bool = False) -> None:
        print(f"[控制台适配器] 踢出群成员: group={group_id}, user={user_id}")

    async def set_group_ban(self, group_id: str, user_id: str, duration: int = 0) -> None:
        action = "禁言" if duration > 0 else "解除禁言"
        print(f"[控制台适配器] {action}群成员: group={group_id}, user={user_id}, duration={duration}")

    async def set_group_whole_ban(self, group_id: str, enable: bool = True) -> None:
        action = "开启" if enable else "关闭"
        print(f"[控制台适配器] {action}全员禁言: group={group_id}")

    async def set_group_admin(self, group_id: str, user_id: str, enable: bool = True) -> None:
        action = "设置" if enable else "取消"
        print(f"[控制台适配器] {action}管理员: group={group_id}, user={user_id}")

    async def handle_friend_request(self, flag: str, approve: bool = True, remark: str = "", **kwargs) -> None:
        action = "同意" if approve else "拒绝"
        print(f"[控制台适配器] {action}好友请求: flag={flag}, remark={remark}")

    async def handle_group_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "", **kwargs) -> None:
        action = "同意" if approve else "拒绝"
        print(f"[控制台适配器] {action}加群请求: flag={flag}, sub_type={sub_type}, reason={reason}")

    # ==================== 扩展API实现 ====================
    async def get_login_info(self) -> Dict[str, Any]:
        return {
            "user_id": self.mock_user_id,
            "nickname": "白面鸮"
        }

    async def set_group_card(self, group_id: str, user_id: str, card: str = "") -> None:
        print(f"[控制台适配器] 设置群名片: group={group_id}, user={user_id}, card={card}")

    async def set_group_name(self, group_id: str, group_name: str) -> None:
        print(f"[控制台适配器] 设置群名: group={group_id}, name={group_name}")

    async def set_group_leave(self, group_id: str, is_dismiss: bool = False) -> None:
        print(f"[控制台适配器] 退出群组: group={group_id}, is_dismiss={is_dismiss}")

    async def send_like(self, user_id: str, times: int = 1) -> None:
        print(f"[控制台适配器] 发送好友赞: user={user_id}, times={times}")

    async def get_forward_msg(self, message_id: str) -> Dict[str, Any]:
        return {
            "message_id": message_id,
            "content": "[合并转发消息]",
            "messages": []
        }

    async def get_self_info(self) -> Dict[str, Any]:
        return await self.get_login_info()

    async def get_status(self) -> Dict[str, Any]:
        return {
            "online": True,
            "good": True,
            "bots": [{
                "self": {"platform": "console", "user_id": self.mock_user_id},
                "online": True
            }]
        }

    async def get_version(self) -> Dict[str, Any]:
        return {
            "impl": "Ptilopsis-Console",
            "version": "1.0.0",
            "onebot_version": "11/12"
        }

    async def get_supported_actions(self) -> List[str]:
        return [
            "send_private_msg", "send_group_msg", "delete_msg", "get_msg",
            "get_login_info", "get_stranger_info", "get_friend_list", "get_group_info",
            "get_group_list", "get_group_member_info", "get_group_member_list",
            "set_group_kick", "set_group_ban", "set_group_whole_ban", "set_group_admin",
            "set_friend_add_request", "set_group_add_request", "set_group_card",
            "set_group_name", "set_group_leave", "send_like", "get_forward_msg",
            "get_self_info", "get_status", "get_version"
        ]

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            "status": "ok",
            "details": {
                "online": True,
                "connected": self._running,
                "running": self._running,
                "mock_user_id": self.mock_user_id,
                "mock_group_id": self.mock_group_id
            }
        }
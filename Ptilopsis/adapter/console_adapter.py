# Ptilopsis/adapter/console_adapter.py
import asyncio
import sys
from typing import Dict, Any, Optional, List, Union
from .base import BaseAdapter
from ..event.base import (
    MessageEvent, PrivateMessageEvent, GroupMessageEvent,
    MessageScene, MessageSegment,
    FriendRequestEvent, GroupRequestEvent,
    GroupMemberIncreaseEvent, GroupMemberDecreaseEvent, GroupBanEvent,
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
        # 模拟场景配置
        self.default_scene = self.config.get("default_scene", "group")
        self.mock_user_id = self.config.get("mock_user_id", "10001")
        self.mock_group_id = self.config.get("mock_group_id", "10000")
        self.mock_nickname = self.config.get("mock_nickname", "博士")
        # 运行状态
        self._running: bool = False
        self._input_task: Optional[asyncio.Task] = None
        # 模拟数据存储
        self._mock_message_id = 0
        self._mock_friend_list = [{"user_id": self.mock_user_id, "nickname": self.mock_nickname}]
        self._mock_group_list = [{"group_id": self.mock_group_id, "group_name": "罗德岛指挥中心"}]
        self._mock_group_member = [
            {"user_id": self.mock_user_id, "nickname": self.mock_nickname, "role": "owner"}
        ]

    async def start(self) -> None:
        """启动控制台适配器，开启输入监听"""
        self._running = True
        print(f"[控制台适配器] 启动成功，默认场景：{self.default_scene}")
        print("[输入消息]: ", end="", flush=True)
        # 启动异步输入监听任务
        self._input_task = asyncio.create_task(self._input_loop())
        # 启动模拟心跳
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """停止适配器，清理资源"""
        self._running = False
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()
        print(f"\n[控制台适配器] 已停止")

    async def _input_loop(self) -> None:
        """异步输入循环，监听控制台输入"""
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                # 异步读取控制台输入
                content = await loop.run_in_executor(None, sys.stdin.readline)
                content = content.strip()
                if not content:
                    print("[输入消息]: ", end="", flush=True)
                    continue

                # 生成消息ID
                self._mock_message_id += 1
                message_id = str(self._mock_message_id)

                # 构建标准消息事件
                if self.default_scene == "private":
                    event = PrivateMessageEvent(
                        adapter=self,
                        raw_event={"content": content},
                        message_id=message_id,
                        user_id=self.mock_user_id,
                        content=content,
                        message=[MessageSegment.text(content)],
                        raw_message=content,
                        sender={"user_id": self.mock_user_id, "nickname": self.mock_nickname}
                    )
                else:
                    event = GroupMessageEvent(
                        adapter=self,
                        raw_event={"content": content},
                        message_id=message_id,
                        user_id=self.mock_user_id,
                        group_id=self.mock_group_id,
                        content=content,
                        message=[MessageSegment.text(content)],
                        raw_message=content,
                        sender={"user_id": self.mock_user_id, "nickname": self.mock_nickname, "role": "owner"}
                    )

                # 发布事件到总线
                await self._publish_event(event)
                print("[输入消息]: ", end="", flush=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n[控制台适配器] 输入处理错误: {e}")
                print("[输入消息]: ", end="", flush=True)

    async def _heartbeat_loop(self) -> None:
        """模拟心跳事件"""
        while self._running:
            await asyncio.sleep(5)
            if self._running:
                event = HeartbeatEvent(self, {}, 5000)
                await self._publish_event(event)

    # ==================== 基类核心方法实现 ====================
    async def send_message(
        self,
        scene: str,
        target_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """发送消息到控制台"""
        # 解析消息内容
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

        # 控制台输出
        scene_name = "私聊" if scene == "private" else "群聊"
        print(f"\n[白面鸮 {scene_name}]: {content}")
        # 生成消息ID
        self._mock_message_id += 1
        return str(self._mock_message_id)

    async def delete_message(self, message_id: str) -> None:
        """模拟撤回消息"""
        print(f"\n[控制台] 已撤回消息 ID: {message_id}")

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """模拟获取消息详情"""
        return {"message_id": message_id, "content": "模拟消息内容"}

    async def get_user_info(self, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """模拟获取用户信息"""
        return {
            "user_id": user_id,
            "nickname": self.mock_nickname if user_id == self.mock_user_id else f"用户{user_id}",
            "age": 0,
            "sex": "unknown"
        }

    async def get_friend_list(self) -> List[Dict[str, Any]]:
        """模拟获取好友列表"""
        return self._mock_friend_list

    async def get_group_info(self, group_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """模拟获取群信息"""
        return {
            "group_id": group_id,
            "group_name": "罗德岛指挥中心",
            "member_count": 10,
            "max_member_count": 200
        }

    async def get_group_list(self) -> List[Dict[str, Any]]:
        """模拟获取群列表"""
        return self._mock_group_list

    async def get_group_member_info(self, group_id: str, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """模拟获取群成员信息"""
        for member in self._mock_group_member:
            if member["user_id"] == user_id:
                return member
        return {"user_id": user_id, "nickname": f"用户{user_id}", "role": "member"}

    async def get_group_member_list(self, group_id: str) -> List[Dict[str, Any]]:
        """模拟获取群成员列表"""
        return self._mock_group_member

    async def set_group_kick(self, group_id: str, user_id: str, reject_add_request: bool = False) -> None:
        """模拟踢出群成员"""
        print(f"\n[控制台] 已踢出群 {group_id} 的用户 {user_id}")

    async def set_group_ban(self, group_id: str, user_id: str, duration: int = 0) -> None:
        """模拟禁言群成员"""
        if duration > 0:
            print(f"\n[控制台] 已禁言群 {group_id} 的用户 {user_id} {duration}秒")
        else:
            print(f"\n[控制台] 已解除群 {group_id} 的用户 {user_id} 的禁言")

    async def set_group_whole_ban(self, group_id: str, enable: bool = True) -> None:
        """模拟全员禁言"""
        status = "开启" if enable else "关闭"
        print(f"\n[控制台] 群 {group_id} 已{status}全员禁言")

    async def set_group_admin(self, group_id: str, user_id: str, enable: bool = True) -> None:
        """模拟设置管理员"""
        status = "设置为" if enable else "取消"
        print(f"\n[控制台] 群 {group_id} 的用户 {user_id} 已{status}管理员")

    async def handle_friend_request(self, flag: str, approve: bool = True, remark: str = "", **kwargs) -> None:
        """模拟处理好友请求"""
        action = "同意" if approve else "拒绝"
        print(f"\n[控制台] 已{action}好友请求，flag: {flag}")

    async def handle_group_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "", **kwargs) -> None:
        """模拟处理加群请求"""
        action = "同意" if approve else "拒绝"
        print(f"\n[控制台] 已{action}加群请求，flag: {flag}")
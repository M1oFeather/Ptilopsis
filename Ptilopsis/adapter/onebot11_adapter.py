# Ptilopsis/adapter/onebot11_adapter.py
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Union
import websockets
from .base import BaseAdapter
from ..event.base import (
    MessageEvent, PrivateMessageEvent, GroupMessageEvent,
    MessageScene, MessageSegment,
    FriendRequestEvent, GroupRequestEvent,
    GroupMemberIncreaseEvent, GroupMemberDecreaseEvent, GroupBanEvent,
    HeartbeatEvent
)


class OneBot11Adapter(BaseAdapter):
    """
    OneBot 11 协议适配器，反向WebSocket实现
    兼容 go-cqhttp、LLOneBot、Shamrock 等主流OneBot 11 实现
    """
    adapter_id = "onebot11"
    platform = "onebot11"

    def __init__(self, core, config: Dict[str, Any] = None):
        super().__init__(core, config)
        # 反向WebSocket配置
        self.ws_host = self.config.get("ws_host", "0.0.0.0")
        self.ws_port = self.config.get("ws_port", 8080)
        self.access_token = self.config.get("access_token", "")
        # 连接管理
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._server: Optional[websockets.WebSocketServer] = None
        self._running: bool = False
        # 动作请求回调
        self._action_futures: Dict[str, asyncio.Future] = {}
        # 心跳配置
        self.heartbeat_interval = self.config.get("heartbeat_interval", 5000)
        # 状态管理
        self.status = {
            "online": False,
            "connected": False,
            "last_heartbeat": 0,
            "error_count": 0
        }
        # 健康检查配置
        self.health_check_interval = self.config.get("health_check_interval", 30)  # 秒

    async def start(self) -> None:
        """启动反向WebSocket服务"""
        self._running = True
        self._server = await websockets.serve(
            self._handle_connection,
            self.ws_host,
            self.ws_port,
            ping_interval=self.heartbeat_interval / 1000,
            ping_timeout=self.heartbeat_interval * 2 / 1000
        )
        # 启动健康检查
        asyncio.create_task(self._health_check())
        print(f"[OneBot11] 反向WebSocket服务已启动，监听 {self.ws_host}:{self.ws_port}")

    async def _health_check(self):
        """健康检查任务"""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                # 检查连接状态
                if self.websocket and self.websocket.open:
                    self.status["connected"] = True
                else:
                    self.status["connected"] = False
                
                # 检查心跳状态
                current_time = asyncio.get_event_loop().time()
                if current_time - self.status["last_heartbeat"] > self.heartbeat_interval * 3 / 1000:
                    self.status["online"] = False
                else:
                    self.status["online"] = True
            except Exception as e:
                print(f"[OneBot11] 健康检查出错: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            "status": "ok" if self.status["online"] and self.status["connected"] else "error",
            "details": {
                "online": self.status["online"],
                "connected": self.status["connected"],
                "last_heartbeat": self.status["last_heartbeat"],
                "error_count": self.status["error_count"],
                "websocket_status": "open" if (self.websocket and self.websocket.open) else "closed"
            }
        }

    async def stop(self) -> None:
        """停止服务，清理资源"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        # 清理所有等待的请求
        for future in self._action_futures.values():
            if not future.done():
                future.cancel()
        self._action_futures.clear()
        print(f"[OneBot11] 适配器已停止")

    async def _handle_connection(self, websocket: websockets.WebSocketServerProtocol):
        """处理WebSocket连接"""
        print(f"[OneBot11] 收到连接请求: {websocket.remote_address}")

        # 校验access_token
        if self.access_token:
            auth_header = websocket.request_headers.get("Authorization", "")
            if auth_header != f"Bearer {self.access_token}":
                await websocket.close(code=401, reason="Unauthorized")
                print(f"[OneBot11] 连接拒绝：鉴权失败")
                return

        self.websocket = websocket
        print(f"[OneBot11] 连接成功: {websocket.remote_address}")

        try:
            async for message in websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[OneBot11] 连接断开: {websocket.remote_address}")
        finally:
            self.websocket = None

    async def _handle_message(self, raw_message: str):
        """处理收到的WebSocket消息"""
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            print(f"[OneBot11] 收到无效JSON: {raw_message}")
            return

        # 处理动作响应
        if "echo" in data:
            echo = data["echo"]
            if echo in self._action_futures:
                future = self._action_futures.pop(echo)
                if not future.done():
                    future.set_result(data)
            return

        # 处理事件上报
        await self._handle_event(data)

    async def _handle_event(self, raw_event: Dict[str, Any]):
        """处理原生事件，转换为框架标准事件并发布"""
        post_type = raw_event.get("post_type")

        # 元事件
        if post_type == "meta_event":
            meta_type = raw_event.get("meta_event_type")
            if meta_type == "heartbeat":
                self.status["last_heartbeat"] = asyncio.get_event_loop().time()
                event = HeartbeatEvent(
                    adapter=self,
                    raw_event=raw_event,
                    interval=raw_event.get("interval", 5000)
                )
                await self._publish_event(event)
            return

        # 消息事件
        if post_type == "message":
            message_type = raw_event.get("message_type")
            message_id = str(raw_event.get("message_id", ""))
            user_id = str(raw_event.get("user_id", ""))
            raw_message = raw_event.get("message", "")
            sender = raw_event.get("sender", {})

            # 解析消息内容
            content = ""
            message_segments = []
            if isinstance(raw_message, str):
                content = raw_message
                message_segments = [MessageSegment.text(raw_message)]
            elif isinstance(raw_message, list):
                content_parts = []
                for seg in raw_message:
                    seg_type = seg.get("type", "")
                    seg_data = seg.get("data", {})
                    message_segments.append(MessageSegment(seg_type, seg_data))
                    if seg_type == "text":
                        content_parts.append(seg_data.get("text", ""))
                content = "".join(content_parts)

            # 私聊消息
            if message_type == "private":
                event = PrivateMessageEvent(
                    adapter=self,
                    raw_event=raw_event,
                    message_id=message_id,
                    user_id=user_id,
                    content=content,
                    message=message_segments,
                    raw_message=raw_message,
                    sender=sender
                )
                await self._publish_event(event)

            # 群聊消息
            elif message_type == "group":
                group_id = str(raw_event.get("group_id", ""))
                event = GroupMessageEvent(
                    adapter=self,
                    raw_event=raw_event,
                    message_id=message_id,
                    user_id=user_id,
                    group_id=group_id,
                    content=content,
                    message=message_segments,
                    raw_message=raw_message,
                    sender=sender
                )
                await self._publish_event(event)
            return

        # 通知事件
        if post_type == "notice":
            notice_type = raw_event.get("notice_type")
            group_id = str(raw_event.get("group_id", ""))
            user_id = str(raw_event.get("user_id", ""))
            operator_id = str(raw_event.get("operator_id", ""))

            if notice_type == "group_increase":
                event = GroupMemberIncreaseEvent(self, raw_event, group_id, user_id, operator_id)
                await self._publish_event(event)
            elif notice_type == "group_decrease":
                event = GroupMemberDecreaseEvent(self, raw_event, group_id, user_id, operator_id)
                await self._publish_event(event)
            elif notice_type == "group_ban":
                duration = raw_event.get("duration", 0)
                event = GroupBanEvent(self, raw_event, group_id, user_id, operator_id, duration)
                await self._publish_event(event)
            return

        # 请求事件
        if post_type == "request":
            request_type = raw_event.get("request_type")
            user_id = str(raw_event.get("user_id", ""))
            comment = raw_event.get("comment", "")
            flag = raw_event.get("flag", "")

            if request_type == "friend":
                event = FriendRequestEvent(self, raw_event, user_id, comment, flag)
                await self._publish_event(event)
            elif request_type == "group":
                sub_type = raw_event.get("sub_type", "")
                group_id = str(raw_event.get("group_id", ""))
                event = GroupRequestEvent(self, raw_event, group_id, user_id, comment, flag, sub_type)
                await self._publish_event(event)
            return

    async def _call_action(self, action: str, params: Dict[str, Any] = None, retry: int = 1) -> Dict[str, Any]:
        """调用OneBot动作API"""
        if not self.websocket or self.websocket.closed:
            raise ConnectionError("OneBot 11 连接未建立")

        echo = str(uuid.uuid4())
        payload = {
            "action": action,
            "params": params or {},
            "echo": echo
        }

        # 创建等待的Future
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._action_futures[echo] = future

        try:
            # 发送请求
            await self.websocket.send(json.dumps(payload))
            # 等待响应，超时30秒
            response = await asyncio.wait_for(future, timeout=30)
            
            # 检查响应状态
            if response.get("status") != "ok":
                retcode = response.get("retcode", -1)
                message = response.get("message", "未知错误")
                raise RuntimeError(f"OneBot 11 动作 {action} 执行失败: {message} (retcode: {retcode})")
            
            return response
        except asyncio.TimeoutError:
            self._action_futures.pop(echo, None)
            if retry > 0:
                print(f"[OneBot11] 动作 {action} 超时，尝试重试...")
                return await self._call_action(action, params, retry=retry-1)
            raise TimeoutError(f"OneBot 11 动作 {action} 响应超时")
        except websockets.exceptions.ConnectionClosed:
            self._action_futures.pop(echo, None)
            raise ConnectionError("OneBot 11 连接已关闭")
        except Exception as e:
            self._action_futures.pop(echo, None)
            raise e

    # ==================== 基类方法实现 ====================
    async def send_message(
            self,
            scene: str,
            target_id: str,
            message: Union[str, List[MessageSegment]],
            **kwargs
    ) -> str:
        action = "send_private_msg" if scene == "private" else "send_group_msg"
        params = {
            "user_id" if scene == "private" else "group_id": int(target_id),
            "message": self._message_to_segments(message),
            **kwargs
        }
        resp = await self._call_action(action, params)
        return str(resp.get("data", {}).get("message_id", ""))

    async def delete_message(self, message_id: str) -> None:
        await self._call_action("delete_msg", {"message_id": int(message_id)})

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        resp = await self._call_action("get_msg", {"message_id": int(message_id)})
        return resp.get("data", {})

    async def get_user_info(self, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        resp = await self._call_action("get_stranger_info", {"user_id": int(user_id), "no_cache": no_cache})
        return resp.get("data", {})

    async def get_friend_list(self) -> List[Dict[str, Any]]:
        resp = await self._call_action("get_friend_list")
        return resp.get("data", [])

    async def get_group_info(self, group_id: str, no_cache: bool = False) -> Dict[str, Any]:
        resp = await self._call_action("get_group_info", {"group_id": int(group_id), "no_cache": no_cache})
        return resp.get("data", {})

    async def get_group_list(self) -> List[Dict[str, Any]]:
        resp = await self._call_action("get_group_list")
        return resp.get("data", [])

    async def get_group_member_info(self, group_id: str, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        resp = await self._call_action("get_group_member_info", {
            "group_id": int(group_id),
            "user_id": int(user_id),
            "no_cache": no_cache
        })
        return resp.get("data", {})

    async def get_group_member_list(self, group_id: str) -> List[Dict[str, Any]]:
        resp = await self._call_action("get_group_member_list", {"group_id": int(group_id)})
        return resp.get("data", [])

    async def set_group_kick(self, group_id: str, user_id: str, reject_add_request: bool = False) -> None:
        await self._call_action("set_group_kick", {
            "group_id": int(group_id),
            "user_id": int(user_id),
            "reject_add_request": reject_add_request
        })

    async def set_group_ban(self, group_id: str, user_id: str, duration: int = 0) -> None:
        await self._call_action("set_group_ban", {
            "group_id": int(group_id),
            "user_id": int(user_id),
            "duration": duration
        })

    async def set_group_whole_ban(self, group_id: str, enable: bool = True) -> None:
        await self._call_action("set_group_whole_ban", {
            "group_id": int(group_id),
            "enable": enable
        })

    async def set_group_admin(self, group_id: str, user_id: str, enable: bool = True) -> None:
        await self._call_action("set_group_admin", {
            "group_id": int(group_id),
            "user_id": int(user_id),
            "enable": enable
        })

    async def handle_friend_request(self, flag: str, approve: bool = True, remark: str = "", **kwargs) -> None:
        await self._call_action("set_friend_add_request", {
            "flag": flag,
            "approve": approve,
            "remark": remark
        })

    async def handle_group_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "",
                                   **kwargs) -> None:
        await self._call_action("set_group_add_request", {
            "flag": flag,
            "sub_type": sub_type,
            "approve": approve,
            "reason": reason
        })

    # ==================== 扩展API实现 ====================
    async def get_login_info(self) -> Dict[str, Any]:
        resp = await self._call_action("get_login_info")
        return resp.get("data", {})

    async def set_group_card(self, group_id: str, user_id: str, card: str = "") -> None:
        await self._call_action("set_group_card", {
            "group_id": int(group_id),
            "user_id": int(user_id),
            "card": card
        })

    async def set_group_name(self, group_id: str, group_name: str) -> None:
        await self._call_action("set_group_name", {
            "group_id": int(group_id),
            "group_name": group_name
        })

    async def set_group_leave(self, group_id: str, is_dismiss: bool = False) -> None:
        await self._call_action("set_group_leave", {
            "group_id": int(group_id),
            "is_dismiss": is_dismiss
        })

    async def send_like(self, user_id: str, times: int = 1) -> None:
        await self._call_action("send_like", {
            "user_id": int(user_id),
            "times": times
        })

    async def get_forward_msg(self, message_id: str) -> Dict[str, Any]:
        resp = await self._call_action("get_forward_msg", {
            "message_id": message_id
        })
        return resp.get("data", {})

    async def get_self_info(self) -> Dict[str, Any]:
        return await self.get_login_info()

    async def get_status(self) -> Dict[str, Any]:
        resp = await self._call_action("get_status")
        return resp.get("data", {})

    async def get_version(self) -> Dict[str, Any]:
        resp = await self._call_action("get_version_info")
        return resp.get("data", {})

    async def get_supported_actions(self) -> List[str]:
        return [
            "send_private_msg", "send_group_msg", "delete_msg", "get_msg",
            "get_login_info", "get_stranger_info", "get_friend_list", "get_group_info",
            "get_group_list", "get_group_member_info", "get_group_member_list",
            "set_group_kick", "set_group_ban", "set_group_whole_ban", "set_group_admin",
            "set_friend_add_request", "set_group_add_request", "set_group_card",
            "set_group_name", "set_group_leave", "send_like", "get_forward_msg",
            "get_status", "get_version_info"
        ]
# Ptilopsis/event/base.py
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Union
from enum import Enum

if TYPE_CHECKING:
    from ..adapter.base import BaseAdapter


# ==================== 枚举定义 ====================
class MessageScene(Enum):
    """消息场景枚举"""
    PRIVATE = "private"  # 私聊
    GROUP = "group"  # 群聊
    CHANNEL = "channel"  # 频道（OneBot 12）


class EventType(Enum):
    """事件类型枚举"""
    # 元事件
    META = "meta"
    # 消息事件
    MESSAGE = "message"
    # 通知事件
    NOTICE = "notice"
    # 请求事件
    REQUEST = "request"


# ==================== 消息段定义 ====================
class MessageSegment:
    """统一消息段，兼容 OneBot 11/12"""

    def __init__(self, type: str, data: Dict[str, Any]):
        self.type = type
        self.data = data

    @staticmethod
    def text(content: str) -> "MessageSegment":
        return MessageSegment("text", {"text": content})

    @staticmethod
    def image(file: str, url: Optional[str] = None) -> "MessageSegment":
        return MessageSegment("image", {"file": file, "url": url})

    @staticmethod
    def at(user_id: Union[str, int], name: Optional[str] = None) -> "MessageSegment":
        return MessageSegment("at", {"qq": str(user_id), "name": name})

    def __str__(self) -> str:
        if self.type == "text":
            return self.data.get("text", "")
        return f"[{self.type}]"


# ==================== 事件基类 ====================
class BaseEvent:
    """所有事件的基类"""
    event_name: str
    event_type: EventType
    adapter: BaseAdapter
    raw_event: Dict[str, Any]  # 协议原生事件
    is_cancelled: bool = False
    is_propagation_stopped: bool = False

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any]):
        self.event_name = self.__class__.__name__
        self.adapter = adapter
        self.raw_event = raw_event

    def cancel(self) -> None:
        """取消事件，后续不忽略取消的监听器将跳过执行"""
        self.is_cancelled = True

    def stop_propagation(self) -> None:
        """阻断事件传播，后续所有监听器一律终止执行"""
        self.is_propagation_stopped = True


# ==================== 元事件 ====================
class MetaEvent(BaseEvent):
    """元事件：心跳、生命周期等"""
    event_type = EventType.META
    meta_type: str

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], meta_type: str):
        super().__init__(adapter, raw_event)
        self.meta_type = meta_type


class HeartbeatEvent(MetaEvent):
    """心跳事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], interval: int):
        super().__init__(adapter, raw_event, "heartbeat")
        self.interval = interval


# ==================== 消息事件（核心，兼容原有逻辑） ====================
class MessageEvent(BaseEvent):
    """通用消息事件，所有平台统一标准"""
    event_type = EventType.MESSAGE
    scene: MessageScene
    message_id: str
    user_id: str
    group_id: Optional[str] = None
    channel_id: Optional[str] = None
    content: str
    message: List[MessageSegment]
    raw_message: Union[str, List[Dict[str, Any]]]
    sender: Dict[str, Any]

    def __init__(
            self,
            adapter: BaseAdapter,
            raw_event: Dict[str, Any],
            scene: MessageScene,
            message_id: str,
            user_id: str,
            content: str,
            message: List[MessageSegment],
            raw_message: Union[str, List[Dict[str, Any]]],
            sender: Dict[str, Any],
            group_id: Optional[str] = None,
            channel_id: Optional[str] = None
    ):
        super().__init__(adapter, raw_event)
        self.scene = scene
        self.message_id = message_id
        self.user_id = user_id
        self.group_id = group_id
        self.channel_id = channel_id
        self.content = content
        self.message = message
        self.raw_message = raw_message
        self.sender = sender

    # ==================== 新增：保持向后兼容的快捷属性 ====================
    @property
    def is_group(self) -> bool:
        """是否为群聊消息（兼容旧版插件）"""
        return self.scene == MessageScene.GROUP

    @property
    def is_private(self) -> bool:
        """是否为私聊消息（兼容旧版插件）"""
        return self.scene == MessageScene.PRIVATE
    # ======================================================================

    async def reply(
            self,
            content: Union[str, List[MessageSegment]],
            auto_escape: bool = False,
            at_sender: bool = False
    ) -> str:
        """
        统一回复接口，兼容原有逻辑，新增增强能力
        :param content: 回复内容，支持纯文本或消息段列表
        :param auto_escape: 是否自动转义特殊字符
        :param at_sender: 是否自动@发送者
        :return: 消息ID
        """
        # 自动@发送者
        if at_sender and self.scene == MessageScene.GROUP:
            if isinstance(content, str):
                content = f"[CQ:at,qq={self.user_id}] {content}"
            else:
                content.insert(0, MessageSegment.at(self.user_id))

        # 发送消息
        if self.scene == MessageScene.PRIVATE:
            return await self.adapter.send_private_message(self.user_id, content)
        elif self.scene == MessageScene.GROUP:
            return await self.adapter.send_group_message(self.group_id, content)
        elif self.scene == MessageScene.CHANNEL:
            return await self.adapter.send_channel_message(self.guild_id, self.channel_id, content)
        return ""

    async def delete(self) -> None:
        """撤回本条消息"""
        await self.adapter.delete_message(self.message_id)


# 兼容原有子类
class PrivateMessageEvent(MessageEvent):
    """私聊消息事件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, scene=MessageScene.PRIVATE, **kwargs)


class GroupMessageEvent(MessageEvent):
    """群聊消息事件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, scene=MessageScene.GROUP, **kwargs)


# ==================== 通知事件 ====================
class NoticeEvent(BaseEvent):
    """通知事件：群成员增减、消息撤回、禁言等"""
    event_type = EventType.NOTICE
    notice_type: str

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], notice_type: str):
        super().__init__(adapter, raw_event)
        self.notice_type = notice_type


class GroupMemberIncreaseEvent(NoticeEvent):
    """群成员增加事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, operator_id: str):
        super().__init__(adapter, raw_event, "group_member_increase")
        self.group_id = group_id
        self.user_id = user_id
        self.operator_id = operator_id


class GroupMemberDecreaseEvent(NoticeEvent):
    """群成员减少事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, operator_id: str):
        super().__init__(adapter, raw_event, "group_member_decrease")
        self.group_id = group_id
        self.user_id = user_id
        self.operator_id = operator_id


class GroupBanEvent(NoticeEvent):
    """群禁言事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, operator_id: str,
                 duration: int):
        super().__init__(adapter, raw_event, "group_ban")
        self.group_id = group_id
        self.user_id = user_id
        self.operator_id = operator_id
        self.duration = duration


# ==================== 请求事件 ====================
class RequestEvent(BaseEvent):
    """请求事件：加群、加好友请求"""
    event_type = EventType.REQUEST
    request_type: str

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], request_type: str):
        super().__init__(adapter, raw_event)
        self.request_type = request_type


class FriendRequestEvent(RequestEvent):
    """加好友请求事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], user_id: str, comment: str, flag: str):
        super().__init__(adapter, raw_event, "friend_request")
        self.user_id = user_id
        self.comment = comment
        self.flag = flag

    async def approve(self, remark: str = "") -> None:
        """同意好友请求"""
        await self.adapter.handle_friend_request(self.flag, approve=True, remark=remark)

    async def reject(self, reason: str = "") -> None:
        """拒绝好友请求"""
        await self.adapter.handle_friend_request(self.flag, approve=False, reason=reason)


class GroupRequestEvent(RequestEvent):
    """加群请求事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, comment: str,
                 flag: str, sub_type: str):
        super().__init__(adapter, raw_event, "group_request")
        self.group_id = group_id
        self.user_id = user_id
        self.comment = comment
        self.flag = flag
        self.sub_type = sub_type

    async def approve(self) -> None:
        """同意加群请求"""
        await self.adapter.handle_group_request(self.flag, self.sub_type, approve=True)

    async def reject(self, reason: str = "") -> None:
        """拒绝加群请求"""
        await self.adapter.handle_group_request(self.flag, self.sub_type, approve=False, reason=reason)
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

    @staticmethod
    def face(id: int) -> "MessageSegment":
        """QQ表情"""
        return MessageSegment("face", {"id": id})

    @staticmethod
    def record(file: str, url: Optional[str] = None) -> "MessageSegment":
        """语音"""
        return MessageSegment("record", {"file": file, "url": url})

    @staticmethod
    def video(file: str, url: Optional[str] = None) -> "MessageSegment":
        """短视频"""
        return MessageSegment("video", {"file": file, "url": url})

    @staticmethod
    def reply(message_id: str) -> "MessageSegment":
        """回复"""
        return MessageSegment("reply", {"id": message_id})

    @staticmethod
    def share(url: str, title: str, content: str = "", image_url: str = "") -> "MessageSegment":
        """链接分享"""
        return MessageSegment("share", {
            "url": url,
            "title": title,
            "content": content,
            "image_url": image_url
        })

    @staticmethod
    def music(type: str, id: str, url: str = "", title: str = "", content: str = "", image_url: str = "") -> "MessageSegment":
        """音乐分享"""
        return MessageSegment("music", {
            "type": type,
            "id": id,
            "url": url,
            "title": title,
            "content": content,
            "image_url": image_url
        })

    @staticmethod
    def forward(nodes: List[Dict]) -> "MessageSegment":
        """合并转发"""
        return MessageSegment("forward", {"content": nodes})

    @staticmethod
    def node(user_id: str, nickname: str, content: Union[str, List["MessageSegment"]], time: int = None) -> Dict:
        """合并转发节点"""
        if isinstance(content, str):
            content = [MessageSegment.text(content)]
        return {
            "user_id": user_id,
            "nickname": nickname,
            "content": content,
            "time": time
        }

    @staticmethod
    def xml(data: str) -> "MessageSegment":
        """XML消息"""
        return MessageSegment("xml", {"data": data})

    @staticmethod
    def json(data: str) -> "MessageSegment":
        """JSON消息"""
        return MessageSegment("json", {"data": data})

    @staticmethod
    def poke(user_id: Union[str, int]) -> "MessageSegment":
        """戳一戳"""
        return MessageSegment("poke", {"qq": str(user_id)})

    @staticmethod
    def markdown(content: str) -> "MessageSegment":
        """Markdown消息"""
        return MessageSegment("markdown", {"content": content})

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


# ==================== 扩展事件类型 ====================


# ==================== 通知事件扩展 ====================


class GroupRecallEvent(NoticeEvent):
    """群消息撤回事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, operator_id: str, message_id: str):
        super().__init__(adapter, raw_event, "group_recall")
        self.group_id = group_id
        self.user_id = user_id
        self.operator_id = operator_id
        self.message_id = message_id


class FriendRecallEvent(NoticeEvent):
    """好友消息撤回事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], user_id: str, message_id: str):
        super().__init__(adapter, raw_event, "friend_recall")
        self.user_id = user_id
        self.message_id = message_id


class GroupAdminEvent(NoticeEvent):
    """群管理员变动事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, enable: bool):
        super().__init__(adapter, raw_event, "group_admin")
        self.group_id = group_id
        self.user_id = user_id
        self.enable = enable  # True为设置管理员，False为取消管理员


class GroupUploadEvent(NoticeEvent):
    """群文件上传事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, file: Dict[str, Any]):
        super().__init__(adapter, raw_event, "group_upload")
        self.group_id = group_id
        self.user_id = user_id
        self.file = file


class FriendAddEvent(NoticeEvent):
    """好友添加事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], user_id: str):
        super().__init__(adapter, raw_event, "friend_add")
        self.user_id = user_id


class GroupNameUpdateEvent(NoticeEvent):
    """群名称变更事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, group_name: str, operator_id: str):
        super().__init__(adapter, raw_event, "group_name_update")
        self.group_id = group_id
        self.group_name = group_name
        self.operator_id = operator_id


class GroupCardUpdateEvent(NoticeEvent):
    """群名片变更事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, card: str):
        super().__init__(adapter, raw_event, "group_card_update")
        self.group_id = group_id
        self.user_id = user_id
        self.card = card


class GroupHonorUpdateEvent(NoticeEvent):
    """群成员荣誉变更事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, honor_type: str):
        super().__init__(adapter, raw_event, "group_honor_update")
        self.group_id = group_id
        self.user_id = user_id
        self.honor_type = honor_type


class PokeEvent(NoticeEvent):
    """戳一戳事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], user_id: str, target_id: str, group_id: str = None):
        super().__init__(adapter, raw_event, "poke")
        self.user_id = user_id
        self.target_id = target_id
        self.group_id = group_id


class GroupLuckyKingEvent(NoticeEvent):
    """群红包运气王事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], group_id: str, user_id: str, lucky_king_id: str):
        super().__init__(adapter, raw_event, "group_lucky_king")
        self.group_id = group_id
        self.user_id = user_id  # 发红包的人
        self.lucky_king_id = lucky_king_id  # 运气王


# ==================== 消息事件扩展 ====================


class ChannelMessageEvent(MessageEvent):
    """频道消息事件（OneBot 12）"""

    def __init__(self, *args, guild_id: str, channel_id: str, **kwargs):
        super().__init__(*args, scene=MessageScene.CHANNEL, channel_id=channel_id, **kwargs)
        self.guild_id = guild_id

    async def reply(
            self,
            content: Union[str, List[MessageSegment]],
            auto_escape: bool = False,
            at_sender: bool = False
    ) -> str:
        """回复频道消息"""
        if at_sender:
            if isinstance(content, str):
                content = f"[CQ:at,qq={self.user_id}] {content}"
            else:
                content.insert(0, MessageSegment.at(self.user_id))
        return await self.adapter.send_channel_message(self.guild_id, self.channel_id, content)


# ==================== 元事件扩展 ====================


class LifecycleEvent(MetaEvent):
    """生命周期事件"""

    def __init__(self, adapter: BaseAdapter, raw_event: Dict[str, Any], lifecycle_type: str):
        super().__init__(adapter, raw_event, "lifecycle")
        self.lifecycle_type = lifecycle_type  # enable、disable、connect、disconnect等
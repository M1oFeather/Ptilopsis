# Ptilopsis/adapter/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from ..event.base import MessageSegment, BaseEvent

class BaseAdapter(ABC):
    """
    适配器抽象基类，基于OneBot 11/12标准定义完整接口
    所有平台适配器必须继承此类并实现所有抽象方法
    """
    # 适配器唯一ID
    adapter_id: str
    # 平台名称
    platform: str
    # 适配器配置
    config: Dict[str, Any]
    # 框架核心实例
    core: Any

    def __init__(self, core, config: Dict[str, Any] = None):
        self.core = core
        self.config = config or {}
        self.adapter_id = self.config.get("adapter_id", self.__class__.__name__)
        self.platform = self.config.get("platform", "unknown")

    @abstractmethod
    async def start(self) -> None:
        """启动适配器，建立连接、初始化资源"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止适配器，关闭连接、清理资源"""
        pass

    # ==================== 核心消息发送接口 ====================
    @abstractmethod
    async def send_message(
        self,
        scene: str,
        target_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """
        通用消息发送接口
        :param scene: 消息场景 private/group/channel
        :param target_id: 目标ID（用户ID/群ID/频道ID）
        :param message: 消息内容，支持纯文本或消息段列表
        :return: 消息ID
        """
        pass

    async def send_private_message(
        self,
        user_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """发送私聊消息"""
        return await self.send_message("private", user_id, message, **kwargs)

    async def send_group_message(
        self,
        group_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """发送群聊消息"""
        return await self.send_message("group", group_id, message, **kwargs)

    async def send_channel_message(
        self,
        guild_id: str,
        channel_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """发送频道消息（OneBot 12）"""
        return await self.send_message("channel", channel_id, message, guild_id=guild_id, **kwargs)

    # ==================== 消息管理接口 ====================
    @abstractmethod
    async def delete_message(self, message_id: str) -> None:
        """撤回消息"""
        pass

    @abstractmethod
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """获取消息详情"""
        pass

    # ==================== 用户信息接口 ====================
    @abstractmethod
    async def get_user_info(self, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """获取用户信息"""
        pass

    @abstractmethod
    async def get_friend_list(self) -> List[Dict[str, Any]]:
        """获取好友列表"""
        pass

    # ==================== 群信息接口 ====================
    @abstractmethod
    async def get_group_info(self, group_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """获取群信息"""
        pass

    @abstractmethod
    async def get_group_list(self) -> List[Dict[str, Any]]:
        """获取群列表"""
        pass

    @abstractmethod
    async def get_group_member_info(self, group_id: str, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """获取群成员信息"""
        pass

    @abstractmethod
    async def get_group_member_list(self, group_id: str) -> List[Dict[str, Any]]:
        """获取群成员列表"""
        pass

    # ==================== 群管理接口 ====================
    @abstractmethod
    async def set_group_kick(self, group_id: str, user_id: str, reject_add_request: bool = False) -> None:
        """踢出群成员"""
        pass

    @abstractmethod
    async def set_group_ban(self, group_id: str, user_id: str, duration: int = 0) -> None:
        """禁言群成员，duration为禁言时长（秒），0为解除禁言"""
        pass

    @abstractmethod
    async def set_group_whole_ban(self, group_id: str, enable: bool = True) -> None:
        """群全员禁言"""
        pass

    @abstractmethod
    async def set_group_admin(self, group_id: str, user_id: str, enable: bool = True) -> None:
        """设置/取消群管理员"""
        pass

    # ==================== 请求处理接口 ====================
    @abstractmethod
    async def handle_friend_request(self, flag: str, approve: bool = True, remark: str = "", **kwargs) -> None:
        """处理加好友请求"""
        pass

    @abstractmethod
    async def handle_group_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "", **kwargs) -> None:
        """处理加群请求"""
        pass

    # ==================== 内部工具方法 ====================
    async def _publish_event(self, event: BaseEvent) -> None:
        """将事件发布到事件总线"""
        await self.core.event_bus.publish(event)

    def _message_to_segments(self, message: Union[str, List[MessageSegment]]) -> List[Dict[str, Any]]:
        """将统一消息段转换为协议原生消息段"""
        if isinstance(message, str):
            return [{"type": "text", "data": {"text": message}}]
        return [{"type": seg.type, "data": seg.data} for seg in message]
# -*- coding: utf-8 -*-
"""
Ptilopsis Adapter Base
适配器抽象基类 - 完整设计版本
支持多平台扩展的能力检测、配置标准化、统一消息模型
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Set
from enum import Enum, auto
from dataclasses import dataclass

from ..event.base import MessageSegment, BaseEvent, MessageScene


class AdapterFeature(Enum):
    """适配器能力枚举 - 标准化功能支持检测"""
    # 消息相关
    SEND_PRIVATE_MESSAGE = auto()
    SEND_GROUP_MESSAGE = auto()
    SEND_CHANNEL_MESSAGE = auto()
    DELETE_MESSAGE = auto()
    GET_MESSAGE = auto()
    SEND_MEDIA = auto()
    
    # 用户相关
    GET_USER_INFO = auto()
    GET_FRIEND_LIST = auto()
    SEND_LIKE = auto()
    
    # 群相关
    GET_GROUP_INFO = auto()
    GET_GROUP_LIST = auto()
    GET_GROUP_MEMBER_INFO = auto()
    GET_GROUP_MEMBER_LIST = auto()
    SET_GROUP_KICK = auto()
    SET_GROUP_BAN = auto()
    SET_GROUP_WHOLE_BAN = auto()
    SET_GROUP_ADMIN = auto()
    SET_GROUP_CARD = auto()
    SET_GROUP_NAME = auto()
    SET_GROUP_PORTRAIT = auto()
    SET_GROUP_LEAVE = auto()
    
    # 请求处理
    HANDLE_FRIEND_REQUEST = auto()
    HANDLE_GROUP_REQUEST = auto()
    
    # 文件相关
    UPLOAD_FILE = auto()
    DOWNLOAD_FILE = auto()
    
    # 系统相关
    GET_SELF_INFO = auto()
    GET_LOGIN_INFO = auto()
    GET_STATUS = auto()
    GET_VERSION = auto()
    GET_SUPPORTED_ACTIONS = auto()
    RESTART = auto()
    
    # 扩展能力
    OCR = auto()
    GET_FORWARD_MESSAGE = auto()
    SET_ESSENCE_MESSAGE = auto()


@dataclass
class ConfigSchemaItem:
    """配置项定义"""
    key: str
    type: type
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None


class BaseAdapter(ABC):
    """
    适配器抽象基类 - 完整设计版本
    所有平台适配器必须继承此类并实现核心抽象方法
    """
    
    # 适配器元信息
    PLATFORM: str = "unknown"
    NAME: str = "Unknown Adapter"
    VERSION: str = "1.0.0"
    
    def __init__(self, core, config: Dict[str, Any] = None):
        self.core = core
        self.config = config or {}
        self.adapter_id = self.config.get("adapter_id", self.__class__.__name__)
        self.platform = self.config.get("platform", self.PLATFORM)
        self.running = False
        
        # 能力缓存
        self._capabilities: Optional[Set[AdapterFeature]] = None
    
    @abstractmethod
    async def start(self) -> None:
        """启动适配器，建立连接、初始化资源"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止适配器，关闭连接、清理资源"""
        pass
    
    # ==================== 能力检测系统 ====================
    
    def get_supported_features(self) -> Set[AdapterFeature]:
        """
        获取适配器支持的所有功能
        子类应重写此方法返回实际支持的功能集合
        """
        if self._capabilities is None:
            self._capabilities = self._init_capabilities()
        return self._capabilities
    
    def _init_capabilities(self) -> Set[AdapterFeature]:
        """初始化能力集合 - 子类重写"""
        return set()
    
    def supports_feature(self, feature: AdapterFeature) -> bool:
        """检测是否支持某功能"""
        return feature in self.get_supported_features()
    
    def get_capabilities_summary(self) -> Dict[str, bool]:
        """获取能力清单摘要"""
        return {feature.name: self.supports_feature(feature) for feature in AdapterFeature}
    
    # ==================== 配置标准化系统 ====================
    
    @classmethod
    def get_config_schema(cls) -> List[ConfigSchemaItem]:
        """
        获取配置项定义
        子类应重写此方法返回配置项列表
        """
        return []
    
    def validate_config(self) -> tuple[bool, List[str]]:
        """
        验证配置是否有效
        返回: (是否有效, 错误信息列表)
        """
        errors = []
        schema = self.get_config_schema()
        
        for item in schema:
            if item.required and item.key not in self.config:
                errors.append(f"缺少必需配置项: {item.key}")
                continue
            
            if item.key in self.config:
                value = self.config[item.key]
                if not isinstance(value, item.type):
                    errors.append(f"配置项 {item.key} 类型错误，期望 {item.type.__name__}")
                    continue
                
                if item.choices and value not in item.choices:
                    errors.append(f"配置项 {item.key} 值无效，可选值: {item.choices}")
        
        return len(errors) == 0, errors
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """安全获取配置项"""
        return self.config.get(key, default)
    
    # ==================== 统一消息模型 ====================
    
    def message_to_native(self, message: Union[str, List[MessageSegment]]) -> Any:
        """
        将统一消息转换为平台原生格式
        子类应重写此方法实现具体转换
        """
        if isinstance(message, str):
            return self._text_to_native(message)
        return self._segments_to_native(message)
    
    def native_to_message(self, native_message: Any) -> List[MessageSegment]:
        """
        将平台原生消息转换为统一消息段
        子类应重写此方法实现具体转换
        """
        return []
    
    def _text_to_native(self, text: str) -> Any:
        """纯文本转原生格式 - 默认实现"""
        return text
    
    def _segments_to_native(self, segments: List[MessageSegment]) -> Any:
        """消息段列表转原生格式 - 默认实现"""
        return [{"type": seg.type, "data": seg.data} for seg in segments]
    
    def extract_plain_text(self, message: Union[str, List[MessageSegment]]) -> str:
        """从消息中提取纯文本"""
        if isinstance(message, str):
            return message
        
        text_parts = []
        for seg in message:
            if seg.type == "text":
                text_parts.append(seg.data.get("text", ""))
        return "".join(text_parts)
    
    # ==================== 核心消息发送接口 ====================
    
    @abstractmethod
    async def send_message(
        self,
        scene: MessageScene,
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
        return await self.send_message(MessageScene.PRIVATE, user_id, message, **kwargs)
    
    async def send_group_message(
        self,
        group_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """发送群聊消息"""
        return await self.send_message(MessageScene.GROUP, group_id, message, **kwargs)
    
    async def send_channel_message(
        self,
        guild_id: str,
        channel_id: str,
        message: Union[str, List[MessageSegment]],
        **kwargs
    ) -> str:
        """发送频道消息"""
        return await self.send_message(
            MessageScene.CHANNEL, 
            channel_id, 
            message, 
            guild_id=guild_id, 
            **kwargs
        )
    
    # ==================== 消息管理接口 ====================
    
    async def delete_message(self, message_id: str) -> None:
        """撤回消息 - 默认实现抛出不支持异常"""
        if not self.supports_feature(AdapterFeature.DELETE_MESSAGE):
            raise NotImplementedError(f"{self.NAME} 不支持撤回消息")
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """获取消息详情 - 默认实现抛出不支持异常"""
        if not self.supports_feature(AdapterFeature.GET_MESSAGE):
            raise NotImplementedError(f"{self.NAME} 不支持获取消息详情")
        return {}
    
    # ==================== 用户信息接口 ====================
    
    async def get_user_info(self, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """获取用户信息"""
        if not self.supports_feature(AdapterFeature.GET_USER_INFO):
            raise NotImplementedError(f"{self.NAME} 不支持获取用户信息")
        return {}
    
    async def get_friend_list(self) -> List[Dict[str, Any]]:
        """获取好友列表"""
        if not self.supports_feature(AdapterFeature.GET_FRIEND_LIST):
            raise NotImplementedError(f"{self.NAME} 不支持获取好友列表")
        return []
    
    # ==================== 群信息接口 ====================
    
    async def get_group_info(self, group_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """获取群信息"""
        if not self.supports_feature(AdapterFeature.GET_GROUP_INFO):
            raise NotImplementedError(f"{self.NAME} 不支持获取群信息")
        return {}
    
    async def get_group_list(self) -> List[Dict[str, Any]]:
        """获取群列表"""
        if not self.supports_feature(AdapterFeature.GET_GROUP_LIST):
            raise NotImplementedError(f"{self.NAME} 不支持获取群列表")
        return []
    
    async def get_group_member_info(self, group_id: str, user_id: str, no_cache: bool = False) -> Dict[str, Any]:
        """获取群成员信息"""
        if not self.supports_feature(AdapterFeature.GET_GROUP_MEMBER_INFO):
            raise NotImplementedError(f"{self.NAME} 不支持获取群成员信息")
        return {}
    
    async def get_group_member_list(self, group_id: str) -> List[Dict[str, Any]]:
        """获取群成员列表"""
        if not self.supports_feature(AdapterFeature.GET_GROUP_MEMBER_LIST):
            raise NotImplementedError(f"{self.NAME} 不支持获取群成员列表")
        return []
    
    # ==================== 群管理接口 ====================
    
    async def set_group_kick(self, group_id: str, user_id: str, reject_add_request: bool = False) -> None:
        """踢出群成员"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_KICK):
            raise NotImplementedError(f"{self.NAME} 不支持踢出群成员")
    
    async def set_group_ban(self, group_id: str, user_id: str, duration: int = 0) -> None:
        """禁言群成员，duration为禁言时长（秒），0为解除禁言"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_BAN):
            raise NotImplementedError(f"{self.NAME} 不支持禁言群成员")
    
    async def set_group_whole_ban(self, group_id: str, enable: bool = True) -> None:
        """群全员禁言"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_WHOLE_BAN):
            raise NotImplementedError(f"{self.NAME} 不支持全员禁言")
    
    async def set_group_admin(self, group_id: str, user_id: str, enable: bool = True) -> None:
        """设置/取消群管理员"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_ADMIN):
            raise NotImplementedError(f"{self.NAME} 不支持设置管理员")
    
    async def set_group_card(self, group_id: str, user_id: str, card: str = "") -> None:
        """设置群名片（群备注）"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_CARD):
            raise NotImplementedError(f"{self.NAME} 不支持设置群名片")
    
    async def set_group_name(self, group_id: str, group_name: str) -> None:
        """设置群名"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_NAME):
            raise NotImplementedError(f"{self.NAME} 不支持设置群名")
    
    async def set_group_leave(self, group_id: str, is_dismiss: bool = False) -> None:
        """退出群组"""
        if not self.supports_feature(AdapterFeature.SET_GROUP_LEAVE):
            raise NotImplementedError(f"{self.NAME} 不支持退出群组")
    
    # ==================== 请求处理接口 ====================
    
    async def handle_friend_request(self, flag: str, approve: bool = True, remark: str = "", **kwargs) -> None:
        """处理加好友请求"""
        if not self.supports_feature(AdapterFeature.HANDLE_FRIEND_REQUEST):
            raise NotImplementedError(f"{self.NAME} 不支持处理好友请求")
    
    async def handle_group_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "", **kwargs) -> None:
        """处理加群请求"""
        if not self.supports_feature(AdapterFeature.HANDLE_GROUP_REQUEST):
            raise NotImplementedError(f"{self.NAME} 不支持处理加群请求")
    
    # ==================== 扩展API ====================
    
    async def get_login_info(self) -> Dict[str, Any]:
        """获取登录号信息（OneBot 11 风格）"""
        if not self.supports_feature(AdapterFeature.GET_LOGIN_INFO):
            raise NotImplementedError(f"{self.NAME} 不支持获取登录信息")
        return {}
    
    async def send_like(self, user_id: str, times: int = 1) -> None:
        """发送好友赞"""
        if not self.supports_feature(AdapterFeature.SEND_LIKE):
            raise NotImplementedError(f"{self.NAME} 不支持发送好友赞")
    
    async def get_forward_msg(self, message_id: str) -> Dict[str, Any]:
        """获取合并转发消息"""
        if not self.supports_feature(AdapterFeature.GET_FORWARD_MESSAGE):
            raise NotImplementedError(f"{self.NAME} 不支持获取合并转发消息")
        return {}
    
    async def get_self_info(self) -> Dict[str, Any]:
        """获取机器人自身信息（OneBot 12 风格）"""
        if not self.supports_feature(AdapterFeature.GET_SELF_INFO):
            raise NotImplementedError(f"{self.NAME} 不支持获取自身信息")
        return {}
    
    async def get_status(self) -> Dict[str, Any]:
        """获取运行状态"""
        if not self.supports_feature(AdapterFeature.GET_STATUS):
            raise NotImplementedError(f"{self.NAME} 不支持获取状态")
        return {}
    
    async def get_version(self) -> Dict[str, Any]:
        """获取版本信息"""
        if not self.supports_feature(AdapterFeature.GET_VERSION):
            raise NotImplementedError(f"{self.NAME} 不支持获取版本信息")
        return {}
    
    async def get_supported_actions(self) -> List[str]:
        """获取支持的动作列表"""
        if not self.supports_feature(AdapterFeature.GET_SUPPORTED_ACTIONS):
            raise NotImplementedError(f"{self.NAME} 不支持获取动作列表")
        return []
    
    # ==================== 事件分发 ====================
    
    async def _dispatch_event(self, event: BaseEvent) -> None:
        """将事件发布到事件总线"""
        if hasattr(self.core, 'event_bus'):
            await self.core.event_bus.publish(event)
    
    # ==================== 适配器信息 ====================
    
    def get_info(self) -> Dict[str, Any]:
        """获取适配器完整信息"""
        return {
            "platform": self.PLATFORM,
            "name": self.NAME,
            "version": self.VERSION,
            "adapter_id": self.adapter_id,
            "running": self.running,
            "capabilities": self.get_capabilities_summary()
        }

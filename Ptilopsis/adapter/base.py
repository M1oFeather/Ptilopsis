# Ptilopsis/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from Ptilopsis.core import Core

class BaseAdapter(ABC):
    """适配器抽象基类，所有平台适配器必须继承此类"""
    adapter_id: str  # 适配器唯一ID
    platform: str    # 平台名称（如QQ、Discord、Telegram）

    def __init__(self, core: Core, config: Dict[str, Any]):
        self.core = core
        self.config = config

    @abstractmethod
    async def start(self) -> None:
        """启动适配器，连接平台服务（如WebSocket、API轮询）"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止适配器，断开连接，清理资源"""
        pass

    @abstractmethod
    async def send_message(self, target: str, content: str) -> None:
        """统一消息发送接口，所有平台共用"""
        pass
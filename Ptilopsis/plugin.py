# Ptilopsis/plugin.py
from abc import ABC, abstractmethod
from .core import Core

class BasePlugin(ABC):
    """插件抽象基类，所有功能插件必须继承"""
    plugin_id: str  # 插件唯一ID，必须设置

    @abstractmethod
    async def load(self, core: Core) -> None:
        """插件加载时执行，用于注册事件监听器、初始化资源"""
        pass

    @abstractmethod
    async def unload(self) -> None:
        """插件卸载时执行，用于清理资源、取消异步任务"""
        pass
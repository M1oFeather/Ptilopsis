"""
Ptilopsis Bot 框架核心包
"""
# 核心运行时
from .core import Core
# 事件系统
from .event.base import BaseEvent, MessageEvent
from .event.bus import EventBus, EventPhase
# 插件系统
from .plugin.base import BasePlugin, Event
from .plugin.manager import PluginManager
from .plugin.archive import PluginArchiveHandler, SecurityError
# 适配器系统
from .adapter.base import BaseAdapter
from .adapter.manager import AdapterManager
# 日志系统
from .logger import log_manager, get_logger, debug, info, warning, error, critical

# 保持原有__all__不变，完全兼容旧代码
__all__ = [
    "Core",
    "BaseEvent",
    "MessageEvent",
    "EventBus",
    "EventPhase",
    "BaseAdapter",
    "AdapterManager",
    "BasePlugin",
    "PluginManager",
    "PluginArchiveHandler",
    "SecurityError",
    "Event",
    # 日志系统
    "log_manager",
    "get_logger",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
]
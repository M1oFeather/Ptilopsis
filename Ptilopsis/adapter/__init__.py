"""
适配器系统子包
"""
from .base import BaseAdapter
from .manager import AdapterManager
from .onebot_base import OneBotAdapter
from .console_adapter import ConsoleAdapter
from .onebot11.adapter import OneBot11Adapter
from .onebot12.adapter import OneBot12Adapter

__all__ = [
    "BaseAdapter",
    "AdapterManager",
    "OneBotAdapter",
    "ConsoleAdapter",
    "OneBot11Adapter",
    "OneBot12Adapter"
]
"""
适配器系统子包
"""
from .base import BaseAdapter
from .manager import AdapterManager
from .console_adapter import ConsoleAdapter
from .onebot11_adapter import OneBot11Adapter
from .onebot12_adapter import OneBot12Adapter

__all__ = [
    "BaseAdapter",
    "AdapterManager",
    "ConsoleAdapter",
    "OneBot11Adapter",
    "OneBot12Adapter"
]
# Ptilopsis/plugin.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .core import Core

class BasePlugin(ABC):
    """插件抽象基类，所有功能插件必须继承"""
    plugin_id: str  # 【必填】插件唯一ID，必须和config.json中的plugin_id一致

    # 插件加载后自动注入的内置属性
    core: Core                      # 框架核心实例
    plugin_info: Dict[str, Any]     # 插件元信息（来自config.json）
    config: Dict[str, Any]          # 合并后的插件配置（默认配置+用户自定义配置）
    base_path: str                  # 插件根目录绝对路径（文件夹/解压后的缓存目录）
    res_path: str                   # 插件资源文件夹res的绝对路径

    @abstractmethod
    async def load(self) -> None:
        """插件加载时执行，用于注册事件监听器、初始化资源"""
        pass

    @abstractmethod
    async def unload(self) -> None:
        """插件卸载时执行，用于清理资源、取消异步任务"""
        pass
# Ptilopsis/core.py
from __future__ import annotations
import asyncio
from typing import Dict, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from .event_bus import EventBus
    from .plugin_manager import PluginManager
    from .adapter_manager import AdapterManager

class Core:
    """框架核心，整合所有模块，管理全局生命周期"""
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._running = False
        # 初始化核心模块
        from .event_bus import EventBus
        from .plugin_manager import PluginManager
        from .adapter_manager import AdapterManager
        self.event_bus: EventBus = EventBus()
        self.plugin_manager: PluginManager = PluginManager(
            self, plugin_dir=self.config.get("plugin_dir", "plugins")
        )
        self.adapter_manager: AdapterManager = AdapterManager(self)

    async def start(self) -> None:
        """启动框架"""
        self._running = True
        # 先加载插件，再启动适配器，避免事件丢失
        await self.plugin_manager.load_all()
        await self.adapter_manager.start_all()
        print("✅ Ptilopsis 框架启动成功")
        # 保持运行
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """停止框架，优雅清理所有资源"""
        self._running = False
        # 先停止适配器，再卸载插件，避免新事件进来
        await self.adapter_manager.stop_all()
        for plugin_id in list(self.plugin_manager._plugins.keys()):
            await self.plugin_manager.unload_plugin(plugin_id)
        print("🛑 Ptilopsis 框架已停止")
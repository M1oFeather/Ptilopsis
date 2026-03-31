# -*- encoding:utf-8 -*-
import asyncio
from typing import Dict, Any

class Core:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._running = False
        # 【修改】更新为单数子包路径
        from .event.bus import EventBus
        from .plugin.manager import PluginManager
        from .adapter.manager import AdapterManager
        self.event_bus: EventBus = EventBus()
        self.plugin_manager: PluginManager = PluginManager(self)
        self.adapter_manager: AdapterManager = AdapterManager(self)

    async def start(self) -> None:
        self._running = True
        await self.plugin_manager.load_all()
        await self.adapter_manager.start_all()
        print("✅ Ptilopsis 框架启动成功")
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        await self.adapter_manager.stop_all()
        for plugin_id in list(self.plugin_manager._plugins.keys()):
            await self.plugin_manager.unload_plugin(plugin_id)
        print("🛑 Ptilopsis 框架已停止")
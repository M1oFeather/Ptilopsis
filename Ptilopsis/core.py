# -*- encoding:utf-8 -*-
import asyncio
import time
from typing import Dict, Any
from .logger import info, error, warning

class Core:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._running = False
        self.loop = None  # 保存主事件循环
        self.start_time = time.time()  # 记录启动时间
        # 【修改】更新为单数子包路径
        from .event.bus import EventBus
        from .plugin.manager import PluginManager
        from .adapter.manager import AdapterManager
        self.event_bus: EventBus = EventBus()
        self.plugin_manager: PluginManager = PluginManager(self)
        self.adapter_manager: AdapterManager = AdapterManager(self)

    async def start(self) -> None:
        self._running = True
        self.start_time = time.time()  # 重新记录启动时间
        self.loop = asyncio.get_running_loop()  # 保存主事件循环
        try:
            await self.plugin_manager.load_all()
            await self.adapter_manager.start_all()
            info("Ptilopsis 框架启动成功", "框架", "核心")
        except Exception as e:
            error(f"框架启动失败: {e}", "框架", "核心")
            raise
        
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        try:
            await self.adapter_manager.stop_all()
            for plugin_id in list(self.plugin_manager._plugins.keys()):
                await self.plugin_manager.unload_plugin(plugin_id)
            info("Ptilopsis 框架已停止", "框架", "核心")
        except Exception as e:
            error(f"框架停止时出错: {e}", "框架", "核心")
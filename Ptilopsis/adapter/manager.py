# -*- coding: utf-8 -*-
from typing import Dict, Optional
# 【修改】更新为相对路径
from .base import BaseAdapter
from ..logger import info, error

class AdapterManager:
    def __init__(self, core):
        self.core = core
        self._adapters: Dict[str, BaseAdapter] = {}

    def add_adapter(self, adapter: BaseAdapter) -> None:
        if adapter.adapter_id in self._adapters:
            raise ValueError(f"适配器 {adapter.adapter_id} 已存在")
        self._adapters[adapter.adapter_id] = adapter

    def create_adapter(self, adapter_type: str, adapter_id: str, config: dict = None) -> BaseAdapter:
        """创建新的适配器实例
        
        Args:
            adapter_type: 适配器类型 (onebot11, onebot12, console)
            adapter_id: 适配器ID
            config: 适配器配置
            
        Returns:
            创建的适配器实例
        """
        config = config or {}
        
        # 把 adapter_id 和 platform 加入到 config 中
        config["adapter_id"] = adapter_id
        config["platform"] = adapter_type
        
        if adapter_type == "onebot11":
            from .onebot11 import OneBot11Adapter
            adapter = OneBot11Adapter(self.core, config=config)
        elif adapter_type == "onebot12":
            from .onebot12 import OneBot12Adapter
            adapter = OneBot12Adapter(self.core, config=config)
        elif adapter_type == "console":
            from .console_adapter import ConsoleAdapter
            adapter = ConsoleAdapter(self.core, config=config)
        else:
            raise ValueError(f"不支持的适配器类型: {adapter_type}")
        
        self.add_adapter(adapter)
        info(f"适配器 {adapter_id} ({adapter_type}) 创建成功", "适配器", adapter_id)
        return adapter

    def remove_adapter(self, adapter_id: str) -> bool:
        """移除适配器"""
        if adapter_id in self._adapters:
            del self._adapters[adapter_id]
            info(f"适配器 {adapter_id} 已移除", "适配器", adapter_id)
            return True
        return False

    async def start_all(self) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.start()
                info(f"{adapter.adapter_id} 启动成功", "适配器", adapter.adapter_id)
            except Exception as e:
                error(f"{adapter.adapter_id} 启动失败: {e}", "适配器", adapter.adapter_id)

    async def stop_all(self) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.stop()
                info(f"{adapter.adapter_id} 已停止", "适配器", adapter.adapter_id)
            except Exception as e:
                error(f"{adapter.adapter_id} 停止失败: {e}", "适配器", adapter.adapter_id)

    def get_adapter(self, adapter_id: str) -> Optional[BaseAdapter]:
        return self._adapters.get(adapter_id)
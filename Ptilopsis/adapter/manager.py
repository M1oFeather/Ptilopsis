# -*- coding: utf-8 -*-
from typing import Dict, Optional
# 【修改】更新为相对路径
from .base import BaseAdapter

class AdapterManager:
    def __init__(self, core):
        self.core = core
        self._adapters: Dict[str, BaseAdapter] = {}

    def add_adapter(self, adapter: BaseAdapter) -> None:
        if adapter.adapter_id in self._adapters:
            raise ValueError(f"适配器 {adapter.adapter_id} 已存在")
        self._adapters[adapter.adapter_id] = adapter

    async def start_all(self) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.start()
                print(f"[适配器] {adapter.adapter_id} 启动成功")
            except Exception as e:
                print(f"[适配器] {adapter.adapter_id} 启动失败: {e}")

    async def stop_all(self) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.stop()
                print(f"[适配器] {adapter.adapter_id} 已停止")
            except Exception as e:
                print(f"[适配器] {adapter.adapter_id} 停止失败: {e}")

    def get_adapter(self, adapter_id: str) -> Optional[BaseAdapter]:
        return self._adapters.get(adapter_id)
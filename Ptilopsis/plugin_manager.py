# Ptilopsis/plugin_manager.py
import os
import sys
import importlib.util
from typing import Dict, Optional, Type
from .core import Core
from .plugin import BasePlugin


class PluginManager:
    def __init__(self, core: Core, plugin_dir: str = "plugins"):
        self.core = core
        self.plugin_dir = plugin_dir
        self._plugins: Dict[str, BasePlugin] = {}  # 插件实例
        self._plugin_meta: Dict[str, dict] = {}  # 插件元信息（模块、路径）
        # 初始化插件目录
        os.makedirs(self.plugin_dir, exist_ok=True)
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)

    def _load_module(self, module_name: str, module_path: str):
        """动态加载模块，避免reload的坑"""
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            raise ImportError(f"无法加载模块 {module_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    async def load_plugin(self, plugin_path: str) -> bool:
        """加载单个插件"""
        full_path = os.path.join(self.plugin_dir, plugin_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"插件不存在: {full_path}")

        # 生成模块名
        module_name = os.path.splitext(os.path.basename(plugin_path))[0]
        # 加载模块
        module = self._load_module(module_name, full_path)

        # 查找插件类
        plugin_class: Optional[Type[BasePlugin]] = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                plugin_class = attr
                break
        if not plugin_class:
            raise ImportError(f"插件 {module_name} 未找到有效的BasePlugin子类")

        # 实例化插件
        plugin = plugin_class()
        plugin_id = plugin.plugin_id
        if not plugin_id:
            raise ValueError(f"插件 {module_name} 未设置plugin_id")
        if plugin_id in self._plugins:
            raise ValueError(f"插件ID {plugin_id} 已存在")

        # 执行插件加载逻辑
        await plugin.load(self.core)
        # 保存插件信息
        self._plugins[plugin_id] = plugin
        self._plugin_meta[plugin_id] = {
            "module": module,
            "module_name": module_name,
            "path": plugin_path
        }
        print(f"[插件] {plugin_id} 加载成功")
        return True

    async def unload_plugin(self, plugin_id: str) -> bool:
        """卸载单个插件，完全清理所有资源"""
        if plugin_id not in self._plugins:
            raise ValueError(f"插件 {plugin_id} 未加载")

        plugin = self._plugins[plugin_id]
        meta = self._plugin_meta[plugin_id]

        # 1. 执行插件卸载逻辑，清理用户资源
        await plugin.unload()
        # 2. 移除插件注册的所有事件监听器
        self.core.event_bus.remove_by_plugin(plugin_id)
        # 3. 完全清理模块引用，解决Python重载残留问题
        module_name = meta["module_name"]
        for key in list(sys.modules.keys()):
            if key == module_name or key.startswith(f"{module_name}."):
                del sys.modules[key]
        # 4. 移除插件缓存
        del self._plugins[plugin_id]
        del self._plugin_meta[plugin_id]

        print(f"[插件] {plugin_id} 卸载成功")
        return True

    async def reload_plugin(self, plugin_id: str) -> bool:
        """热重载插件，无需重启Bot"""
        if plugin_id not in self._plugins:
            raise ValueError(f"插件 {plugin_id} 未加载")
        # 保存插件路径
        plugin_path = self._plugin_meta[plugin_id]["path"]
        # 先卸载，再重新加载
        await self.unload_plugin(plugin_id)
        await self.load_plugin(plugin_path)
        print(f"[插件] {plugin_id} 重载完成")
        return True

    async def load_all(self) -> None:
        """加载插件目录下的所有插件"""
        for filename in os.listdir(self.plugin_dir):
            # 加载单文件插件
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_plugin(filename)
                except Exception as e:
                    print(f"[插件] 加载 {filename} 失败: {e}")
            # 加载插件包
            elif os.path.isdir(os.path.join(self.plugin_dir, filename)):
                init_path = os.path.join(self.plugin_dir, filename, "__init__.py")
                if os.path.exists(init_path):
                    try:
                        await self.load_plugin(os.path.join(filename, "__init__.py"))
                    except Exception as e:
                        print(f"[插件] 加载包 {filename} 失败: {e}")
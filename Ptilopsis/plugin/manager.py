# -*- coding: utf-8 -*-
import os
import sys
import json
import importlib.util
from typing import Dict, Optional, Type
from ..core import Core
from .base import BasePlugin
from .archive import PluginArchiveHandler, SecurityError


class PluginManager:
    def __init__(self, core: Core):
        self.core = core
        self.config = core.config.get("plugin", {})
        self.plugin_dir = self.config.get("plugin_dir", "plugins")
        self.cache_dir = self.config.get("cache_dir", ".cache/plugins")
        self.user_config_dir = self.config.get("user_config_dir", "config/plugins")
        self.allowed_suffixes = self.config.get("allowed_suffixes", [".py", ".pts", ".zip"])

        for dir_path in [self.plugin_dir, self.user_config_dir]:
            os.makedirs(dir_path, exist_ok=True)
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)

        self.archive_handler = PluginArchiveHandler(self.cache_dir, self.allowed_suffixes)
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_meta: Dict[str, dict] = {}

    # ... 其余代码保持不变，只需确保所有内部导入都正确 ...

    def _load_module(self, module_name: str, module_path: str):
        """动态加载模块，解决reload残留问题"""
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            raise ImportError(f"无法加载模块 {module_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _load_plugin_config(self, plugin_base_path: str) -> tuple[dict, dict]:
        """加载插件配置，合并默认配置和用户自定义配置"""
        # 读取插件内置config.json
        config_path = os.path.join(plugin_base_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"插件配置文件不存在: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            plugin_config = json.load(f)

        # 校验必填字段
        required_fields = ["plugin_id", "name", "version"]
        for field in required_fields:
            if field not in plugin_config:
                raise ValueError(f"插件配置缺少必填字段: {field}")

        # 读取用户自定义配置，覆盖默认配置
        plugin_id = plugin_config["plugin_id"]
        user_config_path = os.path.join(self.user_config_dir, f"{plugin_id}.json")
        user_config = {}
        if os.path.exists(user_config_path):
            with open(user_config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)

        # 合并配置
        default_config = plugin_config.get("default_config", {})
        merged_config = {**default_config, **user_config}
        return plugin_config, merged_config

    async def _load_plugin_from_dir(self, plugin_base_path: str) -> bool:
        # 【修改】优先找 main.py，兼容 plugin.py
        plugin_py_path = os.path.join(plugin_base_path, "main.py")
        if not os.path.exists(plugin_py_path):
            # 兼容旧版 plugin.py
            plugin_py_path = os.path.join(plugin_base_path, "plugin.py")
            if not os.path.exists(plugin_py_path):
                raise FileNotFoundError(f"插件主文件不存在: {plugin_base_path}/main.py (或 plugin.py)")

        # ... 其余代码保持不变 ...

        # 加载配置
        plugin_info, merged_config = self._load_plugin_config(plugin_base_path)
        plugin_id = plugin_info["plugin_id"]

        # 加载插件模块
        module_name = f"ptilopsis_plugin_{plugin_id}"
        module = self._load_module(module_name, plugin_py_path)

        # 查找插件类
        plugin_class: Optional[Type[BasePlugin]] = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                plugin_class = attr
                break
        if not plugin_class:
            raise ImportError(f"插件 {plugin_id} 未找到有效的BasePlugin子类")

        # 校验plugin_id一致性
        if plugin_class.plugin_id != plugin_id:
            raise ValueError(f"插件类plugin_id与配置文件不一致: 类中={plugin_class.plugin_id}, 配置中={plugin_id}")

        # 检查插件是否已加载
        if plugin_id in self._plugins:
            raise ValueError(f"插件ID {plugin_id} 已存在，无法重复加载")

        # 实例化插件，注入内置属性
        plugin = plugin_class()
        plugin.core = self.core
        plugin.plugin_info = plugin_info
        plugin.config = merged_config
        plugin.base_path = os.path.abspath(plugin_base_path)
        # 【修改】res改为resource
        plugin.res_path = os.path.abspath(os.path.join(plugin_base_path, "resource"))
        plugin.plugin_priority = plugin_info.get("priority", 0)

        # 执行插件加载逻辑
        await plugin.load()
        # 保存插件元信息
        self._plugins[plugin_id] = plugin
        self._plugin_meta[plugin_id] = {
            "type": "dir",
            "base_path": plugin_base_path,
            "module": module,
            "module_name": module_name
        }
        print(f"[插件] {plugin_id} v{plugin_info['version']} 加载成功")
        return True

    async def load_plugin(self, plugin_name: str) -> bool:
        """
        统一插件加载入口，自动识别插件类型
        :param plugin_name: 插件名（单文件名、文件夹名、压缩包名，带后缀）
        """
        plugin_path = os.path.join(self.plugin_dir, plugin_name)
        if not os.path.exists(plugin_path):
            raise FileNotFoundError(f"插件不存在: {plugin_path}")

        # 1. 处理压缩包插件
        if os.path.isfile(plugin_path) and self.archive_handler.is_archive_plugin(plugin_path):
            try:
                plugin_cache_dir = self.archive_handler.extract_archive(plugin_path)
                return await self._load_plugin_from_dir(plugin_cache_dir)
            except SecurityError as e:
                print(f"[插件] 加载 {plugin_name} 失败: {e}")
                return False

        # 2. 处理文件夹插件
        if os.path.isdir(plugin_path):
            return await self._load_plugin_from_dir(plugin_path)

        # 3. 处理单文件py插件（兼容旧版）
        if os.path.isfile(plugin_path) and plugin_path.endswith(".py"):
            module_name = os.path.splitext(plugin_name)[0]
            module = self._load_module(module_name, plugin_path)
            # 查找插件类
            plugin_class: Optional[Type[BasePlugin]] = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr != BasePlugin:
                    plugin_class = attr
                    break
            if not plugin_class:
                raise ImportError(f"单文件插件 {module_name} 未找到有效的BasePlugin子类")
            plugin_id = plugin_class.plugin_id
            if plugin_id in self._plugins:
                raise ValueError(f"插件ID {plugin_id} 已存在")
            # 实例化插件
            plugin = plugin_class()
            plugin.core = self.core
            plugin.plugin_info = {"plugin_id": plugin_id, "name": plugin_id, "version": "1.0.0"}
            plugin.config = {}
            plugin.base_path = os.path.abspath(self.plugin_dir)
            # 【修改】res改为resource，且不主动创建文件夹
            plugin.res_path = os.path.abspath(os.path.join(self.plugin_dir, "resource", plugin_id))
            # 【删除】os.makedirs(plugin.res_path, exist_ok=True) 这一行
            # 执行加载
            await plugin.load()
            self._plugins[plugin_id] = plugin
            self._plugin_meta[plugin_id] = {
                "type": "single_file",
                "path": plugin_path,
                "module": module,
                "module_name": module_name
            }
            print(f"[插件] 单文件 {plugin_id} 加载成功")
            return True

        raise ValueError(f"不支持的插件格式: {plugin_name}")

    async def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件，完全清理所有资源"""
        if plugin_id not in self._plugins:
            raise ValueError(f"插件 {plugin_id} 未加载")

        plugin = self._plugins[plugin_id]
        meta = self._plugin_meta[plugin_id]

        # 1. 执行插件卸载逻辑
        await plugin.unload()
        # 2. 移除插件注册的所有事件监听器
        self.core.event_bus.remove_by_plugin(plugin_id)
        # 3. 清理模块引用
        module_name = meta["module_name"]
        for key in list(sys.modules.keys()):
            if key == module_name or key.startswith(f"{module_name}."):
                del sys.modules[key]
        # 4. 清理缓存（压缩包插件）
        if meta["type"] == "dir":
            self.archive_handler.clean_cache(plugin_id)
        # 5. 移除插件记录
        del self._plugins[plugin_id]
        del self._plugin_meta[plugin_id]

        print(f"[插件] {plugin_id} 卸载成功")
        return True

    async def reload_plugin(self, plugin_id: str) -> bool:
        """热重载插件，无需重启Bot"""
        if plugin_id not in self._plugins:
            raise ValueError(f"插件 {plugin_id} 未加载")

        meta = self._plugin_meta[plugin_id]
        # 获取插件原始路径
        if meta["type"] == "single_file":
            plugin_name = os.path.basename(meta["path"])
        else:
            plugin_name = os.path.basename(meta["base_path"])

        # 先卸载，再重新加载
        await self.unload_plugin(plugin_id)
        await self.load_plugin(plugin_name)
        print(f"[插件] {plugin_id} 热重载完成")
        return True

    async def load_all(self) -> None:
        """加载插件目录下的所有合法插件，过滤缓存和隐藏文件"""
        for filename in os.listdir(self.plugin_dir):
            file_path = os.path.join(self.plugin_dir, filename)
            try:
                # 新增：过滤隐藏文件、__pycache__目录
                if filename.startswith(".") or filename == "__pycache__":
                    continue
                # 自动识别并加载
                await self.load_plugin(filename)
            except Exception as e:
                print(f"[插件] 加载 {filename} 失败: {e}")
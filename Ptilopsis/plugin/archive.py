# Ptilopsis/archive.py
import os
import json
import zipfile
from typing import Optional, List
from shutil import rmtree


class PluginArchiveHandler:
    """压缩包插件处理器，支持自定义后缀的zip格式压缩包"""

    def __init__(self, cache_dir: str, allowed_suffixes: List[str]):
        self.cache_dir = cache_dir
        self.allowed_suffixes = [s.lower() for s in allowed_suffixes]
        # 初始化缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)
        # 缓存记录文件，保存压缩包的修改时间，用于增量更新
        self.cache_record_path = os.path.join(self.cache_dir, "cache_record.json")
        self._load_cache_record()

    def _load_cache_record(self) -> None:
        """加载缓存记录"""
        if os.path.exists(self.cache_record_path):
            with open(self.cache_record_path, "r", encoding="utf-8") as f:
                self.cache_record = json.load(f)
        else:
            self.cache_record = {}

    def _save_cache_record(self) -> None:
        """保存缓存记录"""
        with open(self.cache_record_path, "w", encoding="utf-8") as f:
            json.dump(self.cache_record, f, ensure_ascii=False, indent=2)

    def is_archive_plugin(self, file_path: str) -> bool:
        """判断文件是否为合法的压缩包插件"""
        if not os.path.isfile(file_path):
            return False
        # 检查后缀是否在允许的列表中
        file_suffix = os.path.splitext(file_path)[1].lower()
        if file_suffix not in self.allowed_suffixes:
            return False
        # 检查是否为合法的zip文件
        return zipfile.is_zipfile(file_path)

    def extract_archive(self, archive_path: str, force: bool = False) -> Optional[str]:
        """
        解压压缩包插件到缓存目录
        :param archive_path: 压缩包文件路径
        :param force: 是否强制重新解压
        :return: 解压后的插件根目录路径，失败返回None
        """
        if not self.is_archive_plugin(archive_path):
            raise ValueError(f"非法的压缩包插件: {archive_path}")

        # 获取压缩包的唯一标识（文件名+修改时间）
        archive_name = os.path.basename(archive_path)
        archive_mtime = os.path.getmtime(archive_path)
        plugin_id = os.path.splitext(archive_name)[0]
        plugin_cache_dir = os.path.join(self.cache_dir, plugin_id)

        # 检查是否需要重新解压
        if not force and plugin_id in self.cache_record:
            if self.cache_record[plugin_id]["mtime"] == archive_mtime and os.path.exists(plugin_cache_dir):
                return plugin_cache_dir

        # 清理旧缓存
        if os.path.exists(plugin_cache_dir):
            rmtree(plugin_cache_dir)
        os.makedirs(plugin_cache_dir, exist_ok=True)

        # 解压压缩包，内置安全防护
        with zipfile.ZipFile(archive_path, "r") as zf:
            # 检查所有文件的路径，防止路径遍历攻击
            for file_info in zf.infolist():
                # 跳过目录
                if file_info.is_dir():
                    continue
                # 规范化路径，防止../跳出缓存目录
                file_path = os.path.normpath(file_info.filename)
                if file_path.startswith("..") or os.path.isabs(file_path):
                    raise SecurityError(f"压缩包包含非法路径，存在路径遍历风险: {file_info.filename}")

                # 解压文件
                zf.extract(file_info, plugin_cache_dir)

        # 更新缓存记录
        self.cache_record[plugin_id] = {
            "archive_path": archive_path,
            "mtime": archive_mtime,
            "cache_dir": plugin_cache_dir
        }
        self._save_cache_record()

        return plugin_cache_dir

    def clean_cache(self, plugin_id: Optional[str] = None) -> None:
        """清理插件缓存，不指定plugin_id则清理全部"""
        if plugin_id:
            if plugin_id in self.cache_record:
                cache_dir = self.cache_record[plugin_id]["cache_dir"]
                if os.path.exists(cache_dir):
                    rmtree(cache_dir)
                del self.cache_record[plugin_id]
                self._save_cache_record()
        else:
            # 清理全部缓存
            if os.path.exists(self.cache_dir):
                rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
            self.cache_record = {}
            self._save_cache_record()


class SecurityError(Exception):
    """插件安全异常"""
    pass
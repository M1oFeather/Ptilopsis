# -*- encoding:utf-8 -*-
"""
Ptilopsis 统一日志管理系统
支持：控制台输出、WebSocket实时推送、文件存储、日志级别控制
日志格式：[时间] [级别] [分类] [子分类] 内容
"""
import asyncio
import logging
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import threading

# ANSI 颜色代码
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


class LogRecord:
    """日志记录数据类"""
    def __init__(self, level: str, message: str, category: str = "其他", sub_category: str = "", timestamp: datetime = None):
        self.level = level
        self.message = message
        self.category = category
        self.sub_category = sub_category
        self.timestamp = timestamp or datetime.now()
        self.time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        self.time_short = self.timestamp.strftime("%H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "category": self.category,
            "sub_category": self.sub_category,
            "time": self.time_str,
            "time_short": self.time_short
        }
    
    def __str__(self):
        if self.sub_category:
            return f"[{self.time_short}] [{self.level}] [{self.category}] [{self.sub_category}] {self.message}"
        return f"[{self.time_short}] [{self.level}] [{self.category}] {self.message}"


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    # 日志级别对应的颜色
    LEVEL_COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.BOLD + Colors.RED,
    }
    
    # 分类对应的颜色
    CATEGORY_COLORS = {
        '框架': Colors.BLUE,
        '插件': Colors.MAGENTA,
        '适配器': Colors.CYAN,
        '其他': Colors.YELLOW,
    }
    
    def __init__(self, fmt=None, datefmt=None, use_colors=True):
        super().__init__(fmt, datefmt)
        # Windows 下默认不使用颜色，除非有 ANSICON 环境变量
        self.use_colors = use_colors and (sys.platform != 'win32' or 'ANSICON' in os.environ)
    
    def format(self, record):
        # 保存原始值
        original_levelname = record.levelname
        original_name = record.name
        
        if self.use_colors:
            # 为级别添加颜色
            level_color = self.LEVEL_COLORS.get(record.levelname, Colors.WHITE)
            record.levelname = f"{level_color}{record.levelname}{Colors.RESET}"
            
            # 为分类添加颜色
            category_color = self.CATEGORY_COLORS.get(getattr(record, 'category', '其他'), Colors.DIM)
            record.name = f"{category_color[0]}{getattr(record, 'category', '其他')}{Colors.RESET}"
        
        # 格式化消息
        result = super().format(record)
        
        # 恢复原始值
        record.levelname = original_levelname
        record.name = original_name
        
        return result


class WebSocketLogHandler(logging.Handler):
    """WebSocket日志处理器 - 将日志推送到前端"""
    
    def __init__(self, log_manager):
        super().__init__()
        self.log_manager = log_manager
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            category = getattr(record, 'category', '其他')
            sub_category = getattr(record, 'sub_category', '')
            
            log_record = LogRecord(level, msg, category, sub_category)
            self.log_manager.add_log(log_record)
        except Exception:
            self.handleError(record)


class CustomFileHandler(logging.Handler):
    """自定义文件处理器 - 实现特定的日志文件存储结构"""
    
    def __init__(self, log_dir: Path, level=logging.NOTSET):
        super().__init__(level)
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 主日志文件
        self.main_log = self.log_dir / "ptilopsis.log"
        # 当前日期 (4位年份，使用-分隔)
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        # 日期归档文件 (使用-分隔)
        self.archive_log = self.log_dir / f"ptilopsis-{self.current_date}.log"
        # error文件夹
        self.error_dir = self.log_dir / "error"
        self.error_dir.mkdir(exist_ok=True)
        # 错误日志文件 (使用-分隔)
        self.error_log = self.error_dir / f"{self.current_date}.log"
        
        # 文件句柄
        self._main_file = None
        self._archive_file = None
        self._error_file = None
        
        # 打开文件
        self._open_files()
    
    def _open_files(self):
        """打开日志文件"""
        self._main_file = open(self.main_log, 'a', encoding='utf-8')
        self._archive_file = open(self.archive_log, 'a', encoding='utf-8')
        self._error_file = open(self.error_log, 'a', encoding='utf-8')
    
    def _close_files(self):
        """关闭文件句柄（不调用父类的close）"""
        if self._main_file:
            self._main_file.close()
            self._main_file = None
        if self._archive_file:
            self._archive_file.close()
            self._archive_file = None
        if self._error_file:
            self._error_file.close()
            self._error_file = None
    
    def _check_date_change(self):
        """检查日期是否变化，如果变化则重新打开文件"""
        new_date = datetime.now().strftime("%Y-%m-%d")
        if new_date != self.current_date:
            # 关闭旧文件（不调用父类的close）
            self._close_files()
            # 更新日期
            self.current_date = new_date
            # 更新文件路径 (使用-分隔)
            self.archive_log = self.log_dir / f"ptilopsis-{self.current_date}.log"
            self.error_log = self.error_dir / f"{self.current_date}.log"
            # 打开新文件
            self._open_files()
    
    def emit(self, record):
        """写入日志记录"""
        try:
            # 检查日期变化
            self._check_date_change()
            
            # 格式化日志（不带颜色）
            msg = str(LogRecord(
                record.levelname,
                record.getMessage(),
                getattr(record, 'category', '其他'),
                getattr(record, 'sub_category', '')
            ))
            
            # 写入主日志文件（最新日志）
            if self._main_file and not self._main_file.closed:
                self._main_file.write(msg + '\n')
                self._main_file.flush()
            
            # 写入日期归档文件
            if self._archive_file and not self._archive_file.closed:
                self._archive_file.write(msg + '\n')
                self._archive_file.flush()
            
            # 如果是ERROR级别及以上，写入错误日志
            if record.levelno >= logging.ERROR and self._error_file and not self._error_file.closed:
                self._error_file.write(msg + '\n')
                self._error_file.flush()
                
        except Exception:
            self.handleError(record)
    
    def close(self):
        """关闭文件句柄"""
        self._close_files()
        super().close()


class DebugFileHandler(logging.Handler):
    """Debug文件处理器 - 保存上一次运行时的全部日志（包括DEBUG）"""
    
    def __init__(self, log_dir: Path):
        super().__init__(logging.DEBUG)
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # debug.log文件路径
        self.debug_log = self.log_dir / "debug.log"
        
        # 如果存在旧的debug.log，删除它（只保留上一次运行的日志）
        if self.debug_log.exists():
            self.debug_log.unlink()
        
        # 打开文件
        self._file = open(self.debug_log, 'w', encoding='utf-8')
    
    def emit(self, record):
        """写入日志记录"""
        try:
            msg = str(LogRecord(
                record.levelname,
                record.getMessage(),
                getattr(record, 'category', '其他'),
                getattr(record, 'sub_category', '')
            ))
            if self._file and not self._file.closed:
                self._file.write(msg + '\n')
                self._file.flush()
        except Exception:
            self.handleError(record)
    
    def close(self):
        """关闭文件句柄"""
        if self._file:
            self._file.close()
            self._file = None
        super().close()


class PrintInterceptor:
    """拦截print函数，将其重定向到日志系统"""
    
    def __init__(self, log_manager):
        self.log_manager = log_manager
        self.original_print = print
    
    def __call__(self, *args, **kwargs):
        # 将print输出转换为日志
        message = ' '.join(str(arg) for arg in args)
        
        # 从消息中提取合适的分类和子分类
        category = "其他"
        sub_category = ""
        
        if message.startswith('[插件]'):
            category = "插件"
            message = message[len('[插件] '):]
        elif message.startswith('[适配器]'):
            category = "适配器"
            message = message[len('[适配器] '):]
        elif message.startswith('[控制台适配器]'):
            category = "适配器"
            sub_category = "ConsoleAdapter"
            message = message[len('[控制台适配器] '):]
        elif message.startswith('[OneBot11]'):
            category = "适配器"
            sub_category = "OneBot11"
            message = message[len('[OneBot11] '):]
        elif message.startswith('[OneBot12]'):
            category = "适配器"
            sub_category = "OneBot12"
            message = message[len('[OneBot12] '):]
        elif message.startswith('[托盘]'):
            category = "框架"
            sub_category = "托盘"
            message = message[len('[托盘] '):]
        elif message.startswith('[输入消息]'):
            category = "适配器"
            message = message[len('[输入消息] '):]
        elif message.startswith('[提示]'):
            category = "其他"
            message = message[len('[提示] '):]
        elif message.startswith('[Web后端]'):
            category = "框架"
            sub_category = "Web后端"
            message = message[len('[Web后端] '):]
        elif message.startswith('[Core]') or message.startswith('[OK]') or message.startswith('[STOP]'):
            category = "框架"
            sub_category = "核心"
        
        self.log_manager.info(message, category, sub_category)
        # 同时调用原始print（用于调试）
        # self.original_print(*args, **kwargs)
    
    def install(self):
        """安装拦截器"""
        import builtins
        builtins.print = self
    
    def uninstall(self):
        """卸载拦截器"""
        import builtins
        builtins.print = self.original_print


class LogManager:
    """
    统一日志管理器
    - 管理所有日志输出
    - 支持WebSocket实时推送
    - 支持日志文件存储
    - 支持日志查询和过滤
    - 完全接管控制台输出
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: str = "logs", max_buffer_size: int = 10000):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_buffer_size = max_buffer_size
        
        # 日志缓冲区
        self._log_buffer: List[LogRecord] = []
        self._buffer_lock = threading.Lock()
        
        # WebSocket回调列表
        self._ws_callbacks: List[Callable] = []
        self._callback_lock = threading.Lock()
        
        # 日志级别
        self._level = logging.INFO
        self._level_names = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        # print拦截器
        self._print_interceptor = PrintInterceptor(self)
        
        # 初始化日志配置
        self._setup_logging()
        
        # 安装print拦截器
        self._print_interceptor.install()
        
        # 输出初始化日志
        self.info("日志系统初始化完成", "框架", "日志管理")
    
    def _setup_logging(self):
        """设置日志配置"""
        # 创建根日志记录器
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(self._level)
        
        # 清除现有处理器
        self.root_logger.handlers.clear()
        
        # 控制台处理器（带颜色）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._level)
        console_format = ColoredFormatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S',
            use_colors=True
        )
        console_handler.setFormatter(console_format)
        self.root_logger.addHandler(console_handler)
        
        # 自定义文件处理器 - 实现特定的日志文件存储结构
        file_handler = CustomFileHandler(self.log_dir, level=self._level)
        file_handler.setLevel(self._level)
        self.root_logger.addHandler(file_handler)
        
        # Debug文件处理器 - 保存上一次运行的全部日志
        debug_handler = DebugFileHandler(self.log_dir)
        debug_handler.setLevel(logging.DEBUG)
        self.root_logger.addHandler(debug_handler)
        
        # WebSocket处理器
        ws_handler = WebSocketLogHandler(self)
        ws_handler.setLevel(self._level)
        ws_handler.setFormatter(logging.Formatter('%(message)s'))
        self.root_logger.addHandler(ws_handler)
    
    def add_log(self, record: LogRecord):
        """添加日志记录"""
        with self._buffer_lock:
            self._log_buffer.append(record)
            # 限制缓冲区大小
            if len(self._log_buffer) > self.max_buffer_size:
                self._log_buffer = self._log_buffer[-self.max_buffer_size:]
        
        # 触发WebSocket回调
        self._notify_ws_callbacks(record)
    
    def _notify_ws_callbacks(self, record: LogRecord):
        """通知所有WebSocket回调"""
        with self._callback_lock:
            callbacks = self._ws_callbacks.copy()
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(record))
                else:
                    callback(record)
            except Exception as e:
                pass
    
    def register_ws_callback(self, callback: Callable):
        """注册WebSocket回调"""
        with self._callback_lock:
            if callback not in self._ws_callbacks:
                self._ws_callbacks.append(callback)
    
    def unregister_ws_callback(self, callback: Callable):
        """注销WebSocket回调"""
        with self._callback_lock:
            if callback in self._ws_callbacks:
                self._ws_callbacks.remove(callback)
    
    def get_logs(self, 
                 level: Optional[str] = None, 
                 category: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0) -> List[Dict[str, Any]]:
        """获取日志记录"""
        with self._buffer_lock:
            logs = self._log_buffer.copy()
        
        # 过滤
        if level:
            logs = [log for log in logs if log.level == level]
        if category:
            logs = [log for log in logs if category.lower() in log.category.lower()]
        
        # 倒序排列（最新的在前）
        logs = logs[::-1]
        
        # 分页
        total = len(logs)
        logs = logs[offset:offset + limit]
        
        return {
            "logs": [log.to_dict() for log in logs],
            "total": total,
            "offset": offset,
            "limit": limit
        }
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        with self._buffer_lock:
            logs = self._log_buffer.copy()
        
        stats = {
            "total": len(logs),
            "by_level": {},
            "by_category": {}
        }
        
        for log in logs:
            # 按级别统计
            stats["by_level"][log.level] = stats["by_level"].get(log.level, 0) + 1
            # 按分类统计
            stats["by_category"][log.category] = stats["by_category"].get(log.category, 0) + 1
        
        return stats
    
    def clear_buffer(self):
        """清空日志缓冲区"""
        with self._buffer_lock:
            self._log_buffer.clear()
    
    def set_level(self, level: str):
        """设置日志级别"""
        if level in self._level_names:
            self._level = self._level_names[level]
            self.root_logger.setLevel(self._level)
            for handler in self.root_logger.handlers:
                if not isinstance(handler, DebugFileHandler):
                    handler.setLevel(self._level)
            self.info(f"日志级别已设置为: {level}", "框架", "日志管理")
    
    def get_level(self) -> str:
        """获取当前日志级别"""
        for name, level in self._level_names.items():
            if level == self._level:
                return name
        return "INFO"
    
    def get_log_files(self) -> List[Dict[str, Any]]:
        """获取日志文件列表"""
        files = []
        if self.log_dir.exists():
            # 主日志文件
            main_log = self.log_dir / "ptilopsis.log"
            if main_log.exists():
                stat = main_log.stat()
                files.append({
                    "name": "ptilopsis.log",
                    "type": "main",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 日期归档文件 (使用-分隔，4位年份)
            for file in self.log_dir.glob("ptilopsis-*.log"):
                stat = file.stat()
                files.append({
                    "name": file.name,
                    "type": "archive",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 错误日志文件
            error_dir = self.log_dir / "error"
            if error_dir.exists():
                for file in error_dir.glob("*.log"):
                    stat = file.stat()
                    files.append({
                        "name": f"error/{file.name}",
                        "type": "error",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            # debug日志文件
            debug_log = self.log_dir / "debug.log"
            if debug_log.exists():
                stat = debug_log.stat()
                files.append({
                    "name": "debug.log",
                    "type": "debug",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return sorted(files, key=lambda x: x["modified"], reverse=True)
    
    def read_log_file(self, filename: str, lines: int = 100) -> List[str]:
        """读取日志文件内容"""
        if filename.startswith("error/"):
            file_path = self.log_dir / "error" / filename[6:]
        else:
            file_path = self.log_dir / filename
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            return [f"读取日志文件失败: {e}"]
    
    # 便捷日志方法 - 按分类输出
    def debug(self, message: str, category: str = "其他", sub_category: str = ""):
        """记录DEBUG级别日志"""
        logger = logging.getLogger(sub_category or "system")
        logger.debug(message, extra={'category': category, 'sub_category': sub_category})
    
    def info(self, message: str, category: str = "其他", sub_category: str = ""):
        """记录INFO级别日志"""
        logger = logging.getLogger(sub_category or "system")
        logger.info(message, extra={'category': category, 'sub_category': sub_category})
    
    def warning(self, message: str, category: str = "其他", sub_category: str = ""):
        """记录WARNING级别日志"""
        logger = logging.getLogger(sub_category or "system")
        logger.warning(message, extra={'category': category, 'sub_category': sub_category})
    
    def error(self, message: str, category: str = "其他", sub_category: str = ""):
        """记录ERROR级别日志"""
        logger = logging.getLogger(sub_category or "system")
        logger.error(message, extra={'category': category, 'sub_category': sub_category})
    
    def critical(self, message: str, category: str = "其他", sub_category: str = ""):
        """记录CRITICAL级别日志"""
        logger = logging.getLogger(sub_category or "system")
        logger.critical(message, extra={'category': category, 'sub_category': sub_category})


# 全局日志管理器实例
log_manager = LogManager()


# 便捷函数
def get_logger(name: str = None):
    """获取日志记录器"""
    return logging.getLogger(name or "system")


def debug(message: str, category: str = "其他", sub_category: str = ""):
    log_manager.debug(message, category, sub_category)


def info(message: str, category: str = "其他", sub_category: str = ""):
    log_manager.info(message, category, sub_category)


def warning(message: str, category: str = "其他", sub_category: str = ""):
    log_manager.warning(message, category, sub_category)


def error(message: str, category: str = "其他", sub_category: str = ""):
    log_manager.error(message, category, sub_category)


def critical(message: str, category: str = "其他", sub_category: str = ""):
    log_manager.critical(message, category, sub_category)


class PluginLogger:
    """插件专用日志对象，在BasePlugin中使用"""
    
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
    
    def debug(self, message: str):
        log_manager.debug(message, "插件", self.plugin_id)
    
    def info(self, message: str):
        log_manager.info(message, "插件", self.plugin_id)
    
    def warning(self, message: str):
        log_manager.warning(message, "插件", self.plugin_id)
    
    def error(self, message: str):
        log_manager.error(message, "插件", self.plugin_id)
    
    def critical(self, message: str):
        log_manager.critical(message, "插件", self.plugin_id)

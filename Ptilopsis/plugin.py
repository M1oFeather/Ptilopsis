from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Coroutine, Callable
from .core import Core
from .event import BaseEvent
from .event_bus import EventPhase  # 【新增】导入EventPhase

class BasePlugin(ABC):
    """插件抽象基类，所有功能插件必须继承"""
    plugin_id: str = ""

    # 插件加载后自动注入的内置属性
    core: Core
    plugin_info: Dict[str, Any]
    config: Dict[str, Any]
    base_path: str
    # 【修改】注释中的res改为resource
    res_path: str  # 插件资源文件夹resource的绝对路径
    plugin_priority: int = 0

    @abstractmethod
    async def load(self) -> None:
        pass

    @abstractmethod
    async def unload(self) -> None:
        pass

    # 【新增】极简挂载装饰器
    def listen(
        self,
        event_type: Type[BaseEvent],
        priority: Optional[int] = None,
        ignore_cancelled: bool = False,
        phase: EventPhase = "normal"
    ):
        use_priority = priority if priority is not None else self.plugin_priority
        return self.core.event_bus.listen(
            event_type=event_type,
            priority=use_priority,
            plugin_id=self.plugin_id,
            ignore_cancelled=ignore_cancelled,
            phase=phase
        )

    # 【新增】别名装饰器，更简短
    def on(
        self,
        event_type: Type[BaseEvent],
        priority: Optional[int] = None,
        ignore_cancelled: bool = False,
        phase: EventPhase = "normal"
    ):
        return self.listen(event_type, priority, ignore_cancelled, phase)
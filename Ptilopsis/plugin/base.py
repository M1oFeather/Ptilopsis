# -*- encoding:utf-8 -*-
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Coroutine, Callable
from ..core import Core
from ..event.base import BaseEvent
from ..event.bus import EventPhase

class BasePlugin(ABC):
    plugin_id: str = ""
    core: Core
    plugin_info: Dict[str, Any]
    config: Dict[str, Any]
    base_path: str
    res_path: str
    plugin_priority: int = 0

    @abstractmethod
    async def load(self) -> None:
        pass

    @abstractmethod
    async def unload(self) -> None:
        pass

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

    def on(
        self,
        event_type: Type[BaseEvent],
        priority: Optional[int] = None,
        ignore_cancelled: bool = False,
        phase: EventPhase = "normal"
    ):
        return self.listen(event_type, priority, ignore_cancelled, phase)
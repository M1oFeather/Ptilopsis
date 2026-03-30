from typing import Callable, Type, Coroutine, Any, List, Tuple, Literal
from functools import wraps
from .event import BaseEvent

# 新增：事件阶段类型定义
EventPhase = Literal["pre", "normal", "post"]


class EventBus:
    def __init__(self):
        # 修改：存储结构改为 事件类型 → 阶段 → 监听器列表
        self._listeners: dict[
            Type[BaseEvent],
            dict[EventPhase, List[Tuple[int, str, Callable[[BaseEvent], Coroutine[Any, Any, None]], bool]]
            ]]= {}

    def listen(
            self,
            event_type: Type[BaseEvent],
            priority: int = 0,
            plugin_id: str = "",
            ignore_cancelled: bool = False,
            # 新增：phase参数，默认normal，兼容旧代码
            phase: EventPhase = "normal"
    ):
        def decorator(func: Callable[[BaseEvent], Coroutine[Any, Any, None]]):
            @wraps(func)
            async def wrapper(event: BaseEvent):
                return await func(event)

            # 初始化阶段存储结构
            if event_type not in self._listeners:
                self._listeners[event_type] = {"pre": [], "normal": [], "post": []}
            if phase not in self._listeners[event_type]:
                raise ValueError(f"非法执行阶段：{phase}，可选值：pre/normal/post")

            self._listeners[event_type][phase].append(
                (priority, plugin_id, wrapper, ignore_cancelled)
            )
            self._listeners[event_type][phase].sort(key=lambda x: -x[0])
            return wrapper

        return decorator

    async def publish(self, event: BaseEvent) -> None:
        """按pre→normal→post顺序执行，支持传播阻断"""
        event_type = type(event)
        if event_type not in self._listeners:
            return

        for phase in ["pre", "normal", "post"]:
            if event.is_propagation_stopped:
                break
            for _, _, listener, ignore_cancelled in self._listeners[event_type][phase]:
                if event.is_propagation_stopped:
                    break
                if event.is_cancelled and not ignore_cancelled:
                    continue
                await listener(event)

    def remove_by_plugin(self, plugin_id: str) -> None:
        """清理所有阶段的监听器"""
        for event_type in self._listeners:
            for phase in self._listeners[event_type]:
                self._listeners[event_type][phase] = [
                    l for l in self._listeners[event_type][phase] if l[1] != plugin_id
                ]
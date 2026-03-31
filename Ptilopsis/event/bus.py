# -*- encoding:utf-8 -*-
from typing import Callable, Type, Coroutine, Any, List, Tuple, Literal
from functools import wraps
# 【修改】更新为相对路径
from .base import BaseEvent

EventPhase = Literal["pre", "normal", "post"]


class EventBus:
    def __init__(self):
        self._listeners: dict[
            Type[BaseEvent],
            dict[EventPhase, List[Tuple[int, str, Callable[[BaseEvent], Coroutine[Any, Any, None]], bool]]
            ]] = {}

    def listen(
            self,
            event_type: Type[BaseEvent],
            priority: int = 0,
            plugin_id: str = "",
            ignore_cancelled: bool = False,
            phase: EventPhase = "normal"
    ):
        def decorator(func: Callable[[BaseEvent], Coroutine[Any, Any, None]]):
            @wraps(func)
            async def wrapper(event: BaseEvent):
                return await func(event)

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
        for event_type in self._listeners:
            for phase in self._listeners[event_type]:
                self._listeners[event_type][phase] = [
                    l for l in self._listeners[event_type][phase] if l[1] != plugin_id
                ]
# Ptilopsis/event_bus.py
from typing import Callable, Type, Coroutine, Any, List, Tuple
from functools import wraps
from .event import BaseEvent


class EventBus:
    def __init__(self):
        # 存储结构：事件类型 -> 监听器列表(优先级, 插件ID, 监听函数, 是否忽略取消)
        self._listeners: dict[
            Type[BaseEvent],
            List[Tuple[int, str, Callable[[BaseEvent], Coroutine[Any, Any, None]], bool]]
        ] = {}

    def listen(
            self,
            event_type: Type[BaseEvent],
            priority: int = 0,
            plugin_id: str = "",
            ignore_cancelled: bool = False
    ):
        """
        事件监听装饰器，Mod式挂载核心
        :param event_type: 要监听的事件类型
        :param priority: 优先级，数值越大越先执行，默认0
        :param plugin_id: 所属插件ID，用于卸载时自动清理
        :param ignore_cancelled: 是否忽略事件取消状态
        """

        def decorator(func: Callable[[BaseEvent], Coroutine[Any, Any, None]]):
            @wraps(func)
            async def wrapper(event: BaseEvent):
                return await func(event)

            # 注册监听器
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(
                (priority, plugin_id, wrapper, ignore_cancelled)
            )
            # 按优先级降序排序，保证高优先级先执行
            self._listeners[event_type].sort(key=lambda x: -x[0])
            return wrapper

        return decorator

    async def publish(self, event: BaseEvent) -> None:
        """发布事件，按优先级顺序执行监听器"""
        event_type = type(event)
        listeners = self._listeners.get(event_type, [])

        for _, _, listener, ignore_cancelled in listeners:
            # 事件已取消且当前监听器不忽略取消，则跳过
            if event.is_cancelled and not ignore_cancelled:
                continue
            await listener(event)

    def remove_by_plugin(self, plugin_id: str) -> None:
        """移除指定插件的所有监听器，卸载插件时自动调用"""
        for event_type in self._listeners:
            self._listeners[event_type] = [
                l for l in self._listeners[event_type] if l[1] != plugin_id
            ]
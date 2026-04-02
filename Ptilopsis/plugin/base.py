# -*- encoding:utf-8 -*-
from abc import ABC, abstractmethod, ABCMeta
from typing import Dict, Any, Optional, Type, Callable, List, Tuple, Literal
from ..core import Core
from ..event.base import BaseEvent
from ..event.bus import EventPhase
from ..logger import PluginLogger

# 定义优先级阶段
PriorityPhase = Literal["pre", "normal", "post"]


# 事件装饰器类
class EventDecorator:
    """事件装饰器类，提供@Event、@Event.Pre、@Event.Post语法"""

    def __init__(self, plugin_cls):
        self.plugin_cls = plugin_cls

    def __call__(
        self,
        event_type: Type[BaseEvent],
        ignore_blocking: bool = False
    ):
        """@Event(MessageEvent) 或 @Event(MessageEvent, ignore_blocking=True) 语法"""
        def decorator(func):
            self.plugin_cls._event_listeners.append((event_type, func, {
                'phase': 'normal',
                'ignore_blocking': ignore_blocking
            }))
            return func
        return decorator

    @property
    def Pre(self):
        """@Event.Pre(MessageEvent, ignore_blocking=True) 语法"""
        def decorator(
            event_type: Type[BaseEvent],
            ignore_blocking: bool = False
        ):
            def wrapper(func):
                self.plugin_cls._event_listeners.append((event_type, func, {
                    'phase': 'pre',
                    'ignore_blocking': ignore_blocking
                }))
                return func
            return wrapper
        return decorator

    @property
    def Post(self):
        """@Event.Post(MessageEvent, ignore_blocking=True) 语法"""
        def decorator(
            event_type: Type[BaseEvent],
            ignore_blocking: bool = False
        ):
            def wrapper(func):
                self.plugin_cls._event_listeners.append((event_type, func, {
                    'phase': 'post',
                    'ignore_blocking': ignore_blocking
                }))
                return func
            return wrapper
        return decorator


# 全局Event对象，用于在类定义时使用
class GlobalEvent:
    """全局Event装饰器，在类定义时自动绑定到当前类"""

    def __call__(
        self,
        event_type: Type[BaseEvent],
        ignore_blocking: bool = False
    ):
        """@Event(MessageEvent) 或 @Event(MessageEvent, ignore_blocking=True) 语法"""
        import inspect
        stack = inspect.stack()
        for frame in stack:
            if frame.function == '<module>':
                locals_dict = frame.frame.f_locals
                for name, obj in locals_dict.items():
                    if isinstance(obj, type) and hasattr(obj, '_event_listeners'):
                        def decorator(func):
                            obj._event_listeners.append((event_type, func, {
                                'phase': 'normal',
                                'ignore_blocking': ignore_blocking
                            }))
                            return func
                        return decorator

        def decorator(func):
            return func
        return decorator

    @property
    def Pre(self):
        """@Event.Pre(MessageEvent, ignore_blocking=True) 语法"""
        import inspect

        def decorator(
            event_type: Type[BaseEvent],
            ignore_blocking: bool = False
        ):
            stack = inspect.stack()
            for frame in stack:
                if frame.function == '<module>':
                    locals_dict = frame.frame.f_locals
                    for name, obj in locals_dict.items():
                        if isinstance(obj, type) and hasattr(obj, '_event_listeners'):
                            def wrapper(func):
                                obj._event_listeners.append((event_type, func, {
                                    'phase': 'pre',
                                    'ignore_blocking': ignore_blocking
                                }))
                                return func
                            return wrapper

            def wrapper(func):
                return func
            return wrapper
        return decorator

    @property
    def Post(self):
        """@Event.Post(MessageEvent, ignore_blocking=True) 语法"""
        import inspect

        def decorator(
            event_type: Type[BaseEvent],
            ignore_blocking: bool = False
        ):
            stack = inspect.stack()
            for frame in stack:
                if frame.function == '<module>':
                    locals_dict = frame.frame.f_locals
                    for name, obj in locals_dict.items():
                        if isinstance(obj, type) and hasattr(obj, '_event_listeners'):
                            def wrapper(func):
                                obj._event_listeners.append((event_type, func, {
                                    'phase': 'post',
                                    'ignore_blocking': ignore_blocking
                                }))
                                return func
                            return wrapper

            def wrapper(func):
                return func
            return wrapper
        return decorator


# 创建全局Event对象
Event = GlobalEvent()


# 元类，用于在类定义时注入Event装饰器
class PluginMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)
        new_cls._event_listeners = []
        return new_cls


class BasePlugin(ABC, metaclass=PluginMeta):
    plugin_id: str = ""
    core: Core
    plugin_info: Dict[str, Any]
    config: Dict[str, Any]
    base_path: str
    res_path: str
    Log: PluginLogger

    @abstractmethod
    async def load(self) -> None:
        pass

    @abstractmethod
    async def unload(self) -> None:
        pass

    def _register_class_event_listeners(self):
        """注册类级别的事件监听器"""
        cls = self.__class__
        for event_type, func, kwargs in cls._event_listeners:
            phase = kwargs.get('phase', 'normal')
            ignore_blocking = kwargs.get('ignore_blocking', False)

            self.core.event_bus.listen(
                event_type=event_type,
                priority=0,
                plugin_id=self.plugin_id,
                ignore_cancelled=ignore_blocking,
                phase=phase
            )(func)

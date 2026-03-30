# -*- encoding:utf-8 -*-
from abc import ABC, abstractmethod


class Target(ABC):
    @abstractmethod
    def operation1(self):
        pass

    @abstractmethod
    def operation2(self):
        pass

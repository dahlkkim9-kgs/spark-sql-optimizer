# backend/core/processors/base_processor.py
from abc import ABC, abstractmethod
from typing import Optional

class BaseProcessor(ABC):
    """SQL 语法处理器基类"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def can_process(self, sql: str) -> bool:
        """判断是否可以处理此 SQL"""
        pass

    @abstractmethod
    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理 SQL 并返回格式化后的结果"""
        pass

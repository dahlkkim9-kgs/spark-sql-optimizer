# backend/core/processors/set_operations.py
from .base_processor import BaseProcessor

class SetOperationsProcessor(BaseProcessor):
    """集合操作处理器 (UNION, INTERSECT, EXCEPT)"""

    def can_process(self, sql: str) -> bool:
        """判断是否可以处理此 SQL"""
        set_operators = ['UNION', 'INTERSECT', 'EXCEPT']
        sql_upper = sql.upper()
        return any(op in sql_upper for op in set_operators)

    def process(self, sql: str, keyword_case: str = 'upper') -> str:
        """处理 SQL 并返回格式化后的结果"""
        # TODO: 实现集合操作格式化逻辑
        return sql

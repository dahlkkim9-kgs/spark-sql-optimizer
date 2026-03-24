# -*- coding: utf-8 -*-
"""括号对齐后处理器

只调整括号缩进，不添加或删除括号
复用 V4 的 IndentContext 进行缩进计算
"""
from typing import List, Tuple
from backend.core.indent_context import IndentContext


class ParenthesisAlignPostProcessor:
    """括号对齐后处理器

    遵循 V4 的 "开括号+1" 规则：
    - 开括号位置 = len(prefix)
    - 内容缩进 = 开括号位置 + 1
    - 闭括号缩进 = 开括号位置
    """

    def __init__(self):
        self.indent_ctx = IndentContext()

    def process(self, sql: str) -> str:
        """调整括号缩进

        Args:
            sql: sqlglot 格式化后的 SQL

        Returns:
            括号缩进调整后的 SQL
        """
        # TODO: 实现
        return sql

    def _find_matching_paren(self, s: str, start: int) -> int:
        """找到匹配的右括号

        Args:
            s: 字符串
            start: 左括号位置

        Returns:
            匹配的右括号位置，-1 表示未找到
        """
        depth = 0
        for i in range(start, len(s)):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1
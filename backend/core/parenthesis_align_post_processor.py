# -*- coding: utf-8 -*-
"""括号对齐后处理器

只调整括号缩进，不添加或删除括号
复用 V4 的 IndentContext 进行缩进计算
"""
from typing import List, Tuple
from backend.core.indent_context import IndentContext
from backend.core.sql_utils import find_matching_paren


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
        return find_matching_paren(s, start)

    def _analyze_line_parens(self, line: str) -> dict:
        """分析一行中的括号信息

        Args:
            line: 一行文本

        Returns:
            dict 包含:
            - has_open_paren: bool
            - has_close_paren: bool
            - open_paren_pos: int (开括号位置，-1 表示无)
            - close_paren_pos: int (闭括号位置，-1 表示无)
            - prefix: str (开括号前的文本)
            - base_indent: int (行首空格数)
        """
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # 查找开括号
        open_pos = stripped.find('(')
        has_open = open_pos >= 0

        # 查找闭括号
        close_pos = stripped.find(')')
        has_close = close_pos >= 0

        # 提取开括号前缀
        if has_open:
            prefix = stripped[:open_pos]
        else:
            prefix = stripped

        return {
            'has_open_paren': has_open,
            'has_close_paren': has_close,
            'open_paren_pos': open_pos if has_open else -1,
            'close_paren_pos': close_pos if has_close else -1,
            'prefix': prefix,
            'base_indent': indent
        }
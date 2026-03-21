# -*- coding: utf-8 -*-
"""
SQL Formatter V5 - 基于 sqlglot AST 解析
结合 v4 的格式化风格
"""
from typing import Optional
from sqlglot import parse, exp
from sqlglot.dialects import Spark


class SQLFormatterV5:
    """基于 sqlglot 的 SQL 格式化器"""

    def __init__(self, indent_spaces: int = 4):
        self.indent_spaces = indent_spaces

    def format(self, sql: str, dialect: str = "spark") -> str:
        """格式化 SQL

        Args:
            sql: 原始 SQL
            dialect: SQL 方言 (默认 spark)

        Returns:
            格式化后的 SQL
        """
        try:
            # 解析为 AST
            ast = parse(sql, dialect=dialect, read=dialect)

            if not ast:
                return sql

            # 使用 sqlglot 内置格式化作为起点
            formatted = ast[0].sql(dialect=dialect, pretty=True, indent=self.indent_spaces)

            return formatted

        except Exception as e:
            # 解析失败时返回原 SQL
            return sql


def format_sql_v5(sql: str, **options) -> str:
    """v5 格式化入口函数"""
    formatter = SQLFormatterV5(
        indent_spaces=options.get('indent', 4)
    )
    return formatter.format(sql)

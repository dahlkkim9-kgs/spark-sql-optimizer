# -*- coding: utf-8 -*-
r"""
SQL Formatter V5 - New Architecture Entry Point

V5 使用 sqlglot 进行语法解析验证，然后使用 V4 进行格式化

优势：
- sqlglot 确保语法解析准确性（复杂嵌套、新语法）
- V4 formatter 保持格式化风格一致性
"""

from typing import Literal

# 导入 sqlglot 版本的 V5
from formatter_v5_sqlglot import format_sql_v5 as format_sql_v5_impl


def format_sql_v5(
    sql: str,
    keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper',
    indent: int = 4
) -> str:
    r"""
    Format SQL using V5 architecture (sqlglot parsing + V4 formatting)

    Args:
        sql: The SQL statement to format
        keyword_case: Keyword case convention ('upper', 'lower', 'capitalize')
        indent: Indentation spaces (default 4)

    Returns:
        Formatted SQL string

    Examples:
        >>> sql = "SELECT a FROM t1 UNION ALL SELECT b FROM t2"
        >>> formatted = format_sql_v5(sql)
        >>> print(formatted)
        SELECT a
             , b
        FROM t1
        UNION ALL
        SELECT b
             , c
        FROM t2
        ;
    """
    if not sql or not sql.strip():
        return sql

    # 调用 sqlglot 版本实现
    return format_sql_v5_impl(sql, indent=indent)


# Compatibility alias
format_sql_v5_new = format_sql_v5

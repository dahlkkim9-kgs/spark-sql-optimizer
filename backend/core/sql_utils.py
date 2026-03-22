# -*- coding: utf-8 -*-
"""
SQL 格式化工具函数 - 共享模块
提供跨格式化器的通用工具函数
"""
from typing import List
import re

# ==================== 常量定义 ====================

# SQL 关键字列表（不应该被当作函数名）
SQL_KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
    'ALTER', 'TRUNCATE', 'ANALYZE', 'GRANT', 'REVOKE', 'MERGE', 'UNION',
    'INTERSECT', 'EXCEPT', 'WITH', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'CROSS', 'ON',
    'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'AND', 'OR', 'NOT',
    'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'DISTINCT', 'ALL',
    'AS', 'ASC', 'DESC', 'BY', 'TABLE', 'VIEW', 'INDEX', 'FUNCTION',
    'PROCEDURE', 'TRIGGER', 'DATABASE', 'SCHEMA', 'TABLESPACE', 'TEMP',
    'TEMPORARY', 'LOCAL', 'GLOBAL', 'SESSION', 'DECLARE', 'BEGIN', 'LOOP',
    'IF', 'FOR', 'WHILE', 'RETURN', 'EXCEPTION', 'GOTO', 'LABEL', 'CALL'
}

# 魔术数字常量
MAX_CONTEXT_LOOKBACK = 150  # 向前查找 CREATE TABLE 的最大字符数
INDENT_MULTIPLIER = 2       # 缩进乘数
NESTING_INDENT_INCREMENT = 4  # 嵌套缩进增量

# 预编译正则表达式
COMMENT_PLACEHOLDER_PATTERN = re.compile(r'__COMMENT_(?:STR_)?\d+__')


# ==================== 工具函数 ====================

def find_matching_paren(s: str, start: int) -> int:
    """找到匹配的右括号位置

    Args:
        s: 字符串
        start: 开始位置（应该是左括号的位置）

    Returns:
        匹配的右括号位置，如果没找到返回 -1
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


def split_by_semicolon(sql: str) -> List[str]:
    """按分号分割 SQL 语句，尊重括号和字符串

    Args:
        sql: SQL 字符串

    Returns:
        分割后的语句列表
    """
    statements = []
    current_stmt = []
    paren_depth = 0
    in_string = False
    string_char = None

    i = 0
    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False

        # 只在非字符串状态下处理括号和分号
        if not in_string:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ';' and paren_depth == 0:
                current_stmt.append(sql[:i+1])
                statements.append(''.join(current_stmt))
                current_stmt = []
                sql = sql[i+1:]
                i = -1  # 会在 i+=1 后变为 0

        i += 1

    # 添加最后一个语句
    if sql.strip():
        current_stmt.append(sql)
        statements.append(''.join(current_stmt))

    return statements

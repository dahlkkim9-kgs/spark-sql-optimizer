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

    def _apply_v4_column_style(self, sql: str) -> str:
        """应用 v4 风格的列对齐

        将:
            SELECT
              a,
              b,
              c
            FROM t1

        转换为:
            SELECT a
                 , b
                 , c
            FROM t1
        """
        lines = sql.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检测 SELECT 子句
            if stripped.startswith('SELECT'):
                # 获取缩进
                indent = line[:line.index('SELECT')]
                result.append(line)  # 先添加 SELECT 行

                # 查找 SELECT 后面的列
                i += 1
                first_column = True
                columns = []

                while i < len(lines):
                    col_line = lines[i].strip()
                    # 检测 FROM/JOIN 等结束列列表
                    if (col_line.startswith('FROM') or
                        col_line.startswith('JOIN') or
                        col_line.startswith('INNER') or
                        col_line.startswith('LEFT') or
                        col_line.startswith('RIGHT') or
                        col_line.startswith('FULL') or
                        col_line.startswith('CROSS') or
                        col_line.startswith('WHERE') or
                        col_line.startswith('GROUP') or
                        col_line.startswith('HAVING') or
                        col_line.startswith('ORDER') or
                        col_line.startswith('LIMIT')):
                        break

                    # 跳过空行
                    if not col_line:
                        i += 1
                        continue

                    # 提取列名（处理逗号）
                    col_name = col_line.rstrip(',').strip()
                    columns.append(col_name)
                    i += 1

                # 格式化列
                if columns:
                    # 第一列合并到 SELECT 行
                    result[-1] = f"{indent}SELECT {columns[0]}"
                    # 后续列使用逗号在行首
                    for col in columns[1:]:
                        result.append(f"{indent}     , {col}")

                # 继续处理（i 已经指向下一行）
                continue

            result.append(line)
            i += 1

        return '\n'.join(result)

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

            # 使用 sqlglot 格式化
            formatted = ast[0].sql(dialect=dialect, pretty=True, indent=self.indent_spaces)

            # 应用 v4 风格后处理
            formatted = self._apply_v4_column_style(formatted)

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

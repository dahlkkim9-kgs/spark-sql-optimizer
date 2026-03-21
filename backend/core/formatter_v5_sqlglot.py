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

        注意：只处理最外层 SELECT 的列，子查询保持原样
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

                # 查找 SELECT 后面的列
                i += 1
                columns = []  # 存储列信息 (type, content)

                while i < len(lines):
                    col_line = lines[i]
                    col_stripped = col_line.strip()

                    # 检测 FROM/JOIN 等结束列列表
                    if (col_stripped.startswith('FROM') or
                        col_stripped.startswith('JOIN') or
                        col_stripped.startswith('INNER') or
                        col_stripped.startswith('LEFT') or
                        col_stripped.startswith('RIGHT') or
                        col_stripped.startswith('FULL') or
                        col_stripped.startswith('CROSS') or
                        col_stripped.startswith('WHERE') or
                        col_stripped.startswith('GROUP') or
                        col_stripped.startswith('HAVING') or
                        col_stripped.startswith('ORDER') or
                        col_stripped.startswith('LIMIT')):
                        break

                    # 跳过空行
                    if not col_stripped:
                        i += 1
                        continue

                    # 检查是否是子查询开始（括号开头）
                    if col_stripped.startswith('('):
                        # 收集子查询的所有行
                        sub_lines = [col_line]
                        i += 1
                        paren_count = col_line.count('(') - col_line.count(')')
                        while i < len(lines) and paren_count > 0:
                            sub_lines.append(lines[i])
                            paren_count += lines[i].count('(') - lines[i].count(')')
                            i += 1
                        # 收集子查询后的别名行（如果有）
                        while i < len(lines):
                            next_stripped = lines[i].strip()
                            # 如果是下一个列（以逗号结尾）或子句关键字，停止
                            if (next_stripped.startswith('FROM') or
                                next_stripped.startswith('WHERE') or
                                next_stripped.endswith(',') or
                                next_stripped.startswith(')')):
                                break
                            # 可能是别名行（AS xxx）
                            if next_stripped.startswith('AS') or ' AS ' in next_stripped:
                                sub_lines.append(lines[i])
                                i += 1
                                break
                            # 其他情况也作为别名行
                            sub_lines.append(lines[i])
                            i += 1
                        columns.append(('subquery', '\n'.join(sub_lines)))
                        continue

                    # 普通列
                    # 移除结尾的逗号
                    col_name = col_stripped.rstrip(',').strip()
                    if col_name:
                        columns.append(('simple', col_name))
                    i += 1

                # 格式化列
                if columns:
                    # 第一列
                    if columns[0][0] == 'simple':
                        result.append(f"{indent}SELECT {columns[0][1]}")
                    else:  # subquery
                        result.append(f"{indent}SELECT")
                        result.append(columns[0][1])

                    # 后续列
                    for col_type, col_content in columns[1:]:
                        if col_type == 'simple':
                            result.append(f"{indent}     , {col_content}")
                        else:  # subquery
                            result.append(f"{indent}     ,")
                            result.append(col_content)
                else:
                    result.append(line)

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

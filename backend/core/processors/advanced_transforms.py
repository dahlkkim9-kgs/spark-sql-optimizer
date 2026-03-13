# -*- coding: utf-8 -*-
r"""
高级转换处理器 - 支持 LATERAL VIEW/PIVOT/UNPIVOT/TRANSFORM/CLUSTER BY/DISTRIBUTE BY

支持的 Spark SQL 高级转换语法:
- LATERAL VIEW [OUTER] EXPLODE(...) table_alias AS column_alias
- LATERAL VIEW JSON_TUPLE(...) table_alias AS column_alias
- PIVOT (基础支持)
- UNPIVOT (基础支持)
- TRANSFORM (基础支持)
- CLUSTER BY
- DISTRIBUTE BY
"""

import re
import sys
import os
from typing import Literal, List, Tuple
from .base_processor import BaseProcessor


def _get_formatter():
    """动态导入 formatter_v4_fixed，兼容不同运行环境"""
    try:
        # 尝试从 backend.core 导入（API 环境）
        from backend.core.formatter_v4_fixed import format_sql_v4_fixed
        return format_sql_v4_fixed
    except ImportError:
        # 尝试从 core 导入（测试环境）
        try:
            # 确保 core 路径在 sys.path 中
            core_path = os.path.join(os.path.dirname(__file__), '..')
            if core_path not in sys.path:
                sys.path.insert(0, core_path)
            from core.formatter_v4_fixed import format_sql_v4_fixed
            return format_sql_v4_fixed
        except ImportError:
            # 最后尝试直接导入
            from formatter_v4_fixed import format_sql_v4_fixed
            return format_sql_v4_fixed


# 缓存导入的函数
_formatter_func = None


def _call_formatter(sql: str, keyword_case: str = 'upper') -> str:
    """调用 formatter_v4_fixed.format_sql_v4_fixed"""
    global _formatter_func
    if _formatter_func is None:
        _formatter_func = _get_formatter()
    return _formatter_func(sql, keyword_case=keyword_case)


class AdvancedTransformsProcessor(BaseProcessor):
    """高级转换处理器 - 支持 LATERAL VIEW/PIVOT/UNPIVOT/TRANSFORM"""

    def __init__(self):
        super().__init__()
        # 高级转换关键字模式
        self.patterns = {
            'lateral_view': re.compile(r'\bLATERAL\s+VIEW\b', re.IGNORECASE),
            'pivot': re.compile(r'\bPIVOT\b', re.IGNORECASE),
            'unpivot': re.compile(r'\bUNPIVOT\b', re.IGNORECASE),
            'transform': re.compile(r'\bTRANSFORM\b', re.IGNORECASE),
            'cluster_by': re.compile(r'\bCLUSTER\s+BY\b', re.IGNORECASE),
            'distribute_by': re.compile(r'\bDISTRIBUTE\s+BY\b', re.IGNORECASE),
        }

    def can_process(self, sql: str) -> bool:
        """检查 SQL 是否包含高级转换语法"""
        if not sql or not sql.strip():
            return False

        sql_upper = sql.upper()
        # 检查 LATERAL VIEW
        if self.patterns['lateral_view'].search(sql):
            return True
        # 检查 PIVOT/UNPIVOT
        if self.patterns['pivot'].search(sql):
            return True
        if self.patterns['unpivot'].search(sql):
            return True
        # 检查 TRANSFORM
        if self.patterns['transform'].search(sql):
            return True
        # 检查 CLUSTER BY
        if self.patterns['cluster_by'].search(sql):
            return True
        # 检查 DISTRIBUTE BY
        if self.patterns['distribute_by'].search(sql):
            return True

        return False

    def process(self, sql: str, keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper') -> str:
        """处理包含高级转换的 SQL"""
        # 去除首尾空白
        sql = sql.strip()

        # 优先处理 LATERAL VIEW（最常见）
        if self.patterns['lateral_view'].search(sql):
            return self._process_lateral_view(sql, keyword_case)

        # 处理 CLUSTER BY / DISTRIBUTE BY
        if self.patterns['cluster_by'].search(sql) or self.patterns['distribute_by'].search(sql):
            return self._process_cluster_distribute(sql, keyword_case)

        # PIVOT/UNPIVOT/TRANSFORM 使用基础格式化（占位实现）
        # 后续可以扩展为专门的处理器
        return self._process_basic_transform(sql, keyword_case)

    def _process_lateral_view(self, sql: str, keyword_case: str) -> str:
        """
        处理 LATERAL VIEW 语句

        格式化规则:
        - LATERAL VIEW 与 FROM 对齐（无缩进）
        - 每个 LATERAL VIEW 独立一行
        - EXPLODE 函数参数可换行
        - 保留后续的 GROUP BY, HAVING 等子句
        - 保留开头和结尾的注释
        """
        # 提取开头的注释（单行 -- 或多行 /* */）
        leading_comment = ''
        sql_without_leading_comment = sql

        # 匹配开头的单行注释
        comment_match = re.match(r'^(\s*--[^\n]*\n)*', sql)
        if comment_match:
            leading_comment = comment_match.group(0)
            sql_without_leading_comment = sql[comment_match.end():]

        # 提取结尾的分号和注释
        trailing_semicolon = ''
        if sql_without_leading_comment.rstrip().endswith(';'):
            trailing_semicolon = ';'

        # 提取 SELECT 和 FROM 子句之间的部分
        select_match = re.match(r'(\s*SELECT\s+.*?\s+FROM\s+.*?)(?=\s*LATERAL\s+VIEW)', sql_without_leading_comment, re.IGNORECASE | re.DOTALL)
        if not select_match:
            # 如果没有匹配到，使用基础格式化
            return _call_formatter(sql, keyword_case)

        select_from_part = select_match.group(1)
        lateral_part = sql_without_leading_comment[select_match.end():].strip()

        # 格式化 SELECT ... FROM 部分
        formatted_select = _call_formatter(select_from_part, keyword_case)

        # 移除末尾的分号（如果有）
        lines = formatted_select.split('\n')
        while lines and (not lines[-1].strip() or lines[-1].strip() == ';'):
            lines.pop()
        formatted_select = '\n'.join(lines)

        # 解析 LATERAL VIEW 语句和后续子句
        lateral_views, remaining_clauses = self._parse_lateral_views_and_clauses(lateral_part)

        # 格式化每个 LATERAL VIEW
        formatted_lateral = []
        for lv in lateral_views:
            formatted_lv = self._format_single_lateral_view(lv, keyword_case)
            formatted_lateral.append(formatted_lv)

        # 组合结果
        result = formatted_select
        if formatted_lateral:
            result += '\n' + '\n'.join(formatted_lateral)

        # 添加后续子句（GROUP BY, HAVING 等）
        if remaining_clauses.strip():
            result += '\n' + remaining_clauses.strip()

        # 添加结尾分号
        if trailing_semicolon:
            result += '\n' + trailing_semicolon

        # 添加开头注释
        if leading_comment:
            result = leading_comment + result

        return result

    def _parse_lateral_views(self, lateral_sql: str) -> List[str]:
        """
        解析多个 LATERAL VIEW 语句

        返回 LATERAL VIEW 语句列表
        """
        lateral_views = []
        current = ""
        i = 0
        paren_depth = 0

        while i < len(lateral_sql):
            char = lateral_sql[i]

            # 跟踪括号深度
            if char == '(':
                paren_depth += 1
                current += char
                i += 1
                continue
            elif char == ')':
                paren_depth -= 1
                current += char
                i += 1
                continue

            # 只在顶层（括号外）检查 LATERAL VIEW
            if paren_depth == 0:
                match = re.match(r'\bLATERAL\s+VIEW\b', lateral_sql[i:], re.IGNORECASE)
                if match:
                    # 如果有累积的内容，先保存
                    if current.strip():
                        lateral_views.append(current.strip())
                    # 开始新的 LATERAL VIEW
                    i += match.end()
                    current = "LATERAL VIEW"
                    continue

            current += char
            i += 1

        # 添加最后一个 LATERAL VIEW
        if current.strip():
            lateral_views.append(current.strip())

        return lateral_views

    def _parse_lateral_views_and_clauses(self, lateral_sql: str) -> tuple[List[str], str]:
        """
        解析 LATERAL VIEW 语句和后续子句

        返回: (LATERAL_VIEW 语句列表, 剩余子句字符串)

        后续子句包括: GROUP BY, HAVING, ORDER BY, LIMIT, etc.
        """
        lateral_views = []
        current = ""
        i = 0
        paren_depth = 0

        # 后续子句的关键字（必须独立成词）
        clause_keywords = [
            r'\bGROUP\s+BY\b',
            r'\bHAVING\b',
            r'\bORDER\s+BY\b',
            r'\bLIMIT\b',
            r'\bOFFSET\b',
            r'\bQUALIFY\b'
        ]

        while i < len(lateral_sql):
            char = lateral_sql[i]

            # 跟踪括号深度
            if char == '(':
                paren_depth += 1
                current += char
                i += 1
                continue
            elif char == ')':
                paren_depth -= 1
                current += char
                i += 1
                continue

            # 只在顶层（括号外）检查
            if paren_depth == 0:
                # 检查是否遇到后续子句
                for clause_pattern in clause_keywords:
                    clause_match = re.match(clause_pattern, lateral_sql[i:], re.IGNORECASE)
                    if clause_match:
                        # 保存当前的 LATERAL VIEW
                        if current.strip():
                            lateral_views.append(current.strip())
                        # 返回剩余的子句（移除结尾的分号）
                        remaining = lateral_sql[i:].strip()
                        if remaining.endswith(';'):
                            remaining = remaining[:-1].strip()
                        return lateral_views, remaining

                # 检查 LATERAL VIEW
                match = re.match(r'\bLATERAL\s+VIEW\b', lateral_sql[i:], re.IGNORECASE)
                if match:
                    # 如果有累积的内容，先保存
                    if current.strip():
                        lateral_views.append(current.strip())
                    # 开始新的 LATERAL VIEW
                    i += match.end()
                    current = "LATERAL VIEW"
                    continue

            current += char
            i += 1

        # 添加最后一个 LATERAL VIEW
        if current.strip():
            lateral_views.append(current.strip())

        return lateral_views, ""

    def _format_single_lateral_view(self, lateral_view: str, keyword_case: str) -> str:
        """
        格式化单个 LATERAL VIEW 语句

        规则:
        - LATERAL VIEW [OUTER] EXPLODE(...) table_alias AS column_alias
        - 关键字大写
        - 函数参数可换行
        """
        # 标准化关键字
        lv = lateral_view.strip()

        # 解析 LATERAL VIEW 组件（在大小写转换之前）
        # 模式: LATERAL VIEW [OUTER] function(...) table_alias AS column_aliases
        pattern = r'(LATERAL\s+VIEW)(\s+OUTER)?(\s+\w+)(\([^)]*\))(\s+\w+)(\s+AS)(\s+.+)'
        match = re.match(pattern, lv, re.IGNORECASE)

        if match:
            lateral_view_kw = match.group(1)  # LATERAL VIEW
            outer_kw = match.group(2) or ''  # OUTER (可选)
            function_name = match.group(3)  # EXPLODE/JSON_TUPLE
            function_args = match.group(4)  # (...)
            table_alias = match.group(5)  # table_alias
            as_kw = match.group(6)  # AS
            column_aliases = match.group(7)  # column_aliases

            # 转换为统一大小写
            if keyword_case == 'upper':
                lateral_view_kw = lateral_view_kw.upper()
                if outer_kw:
                    outer_kw = outer_kw.upper()
                function_name = function_name.upper()
                as_kw = as_kw.upper()
            elif keyword_case == 'lower':
                lateral_view_kw = lateral_view_kw.lower()
                if outer_kw:
                    outer_kw = outer_kw.lower()
                function_name = function_name.lower()
                as_kw = as_kw.lower()
            else:  # capitalize
                lateral_view_kw = lateral_view_kw.capitalize()
                if outer_kw:
                    outer_kw = outer_kw.capitalize()
                function_name = function_name.capitalize()
                as_kw = as_kw.capitalize()

            # 格式化函数参数（如果很长）
            formatted_args = self._format_function_args(function_args)

            # 组装
            result = f"{lateral_view_kw}{outer_kw}{function_name}{formatted_args}{table_alias}{as_kw}{column_aliases}"
            return result.strip()
        else:
            # 如果解析失败，应用全局大小写转换
            if keyword_case == 'upper':
                lv = re.sub(r'\blateral\b', 'LATERAL', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bview\b', 'VIEW', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bouter\b', 'OUTER', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bas\b', 'AS', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bexplode\b', 'EXPLODE', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bjson_tuple\b', 'JSON_TUPLE', lv, flags=re.IGNORECASE)
            elif keyword_case == 'lower':
                lv = re.sub(r'\bLATERAL\b', 'lateral', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bVIEW\b', 'view', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bOUTER\b', 'outer', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bAS\b', 'as', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bEXPLODE\b', 'explode', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bJSON_TUPLE\b', 'json_tuple', lv, flags=re.IGNORECASE)
            else:  # capitalize
                lv = re.sub(r'\bLATERAL\b', 'Lateral', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bVIEW\b', 'View', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bOUTER\b', 'Outer', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bAS\b', 'As', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bEXPLODE\b', 'Explode', lv, flags=re.IGNORECASE)
                lv = re.sub(r'\bJSON_TUPLE\b', 'Json_Tuple', lv, flags=re.IGNORECASE)

            return lv

        if match:
            lateral_view_kw = match.group(1)  # LATERAL VIEW
            outer_kw = match.group(2) or ''  # OUTER (可选)
            function_name = match.group(3)  # EXPLODE/JSON_TUPLE
            function_args = match.group(4)  # (...)
            table_alias = match.group(5)  # table_alias
            as_kw = match.group(6)  # AS
            column_aliases = match.group(7)  # column_aliases

            # 格式化函数参数（如果很长）
            formatted_args = self._format_function_args(function_args)

            # 组装
            result = f"{lateral_view_kw}{outer_kw}{function_name}{formatted_args}{table_alias}{as_kw}{column_aliases}"
            return result.strip()
        else:
            # 如果解析失败，返回原始内容
            return lv

    def _format_function_args(self, args: str) -> str:
        """
        格式化函数参数

        如果参数过长，可以考虑换行
        """
        args = args.strip()
        # 移除外层括号
        if args.startswith('(') and args.endswith(')'):
            inner = args[1:-1].strip()
            # 如果参数简单，直接返回
            if len(inner) < 50:
                return args
            # TODO: 可以实现更复杂的参数换行逻辑
        return args

    def _process_cluster_distribute(self, sql: str, keyword_case: str) -> str:
        """
        处理 CLUSTER BY / DISTRIBUTE BY

        这些子句类似于 ORDER BY，格式化规则相同
        """
        # 在格式化之前先标准化关键字
        processed_sql = sql
        if keyword_case == 'upper':
            processed_sql = re.sub(r'\bCLUSTER\s+BY\b', 'CLUSTER BY', processed_sql, flags=re.IGNORECASE)
            processed_sql = re.sub(r'\bDISTRIBUTE\s+BY\b', 'DISTRIBUTE BY', processed_sql, flags=re.IGNORECASE)
        elif keyword_case == 'lower':
            processed_sql = re.sub(r'\bCLUSTER\s+BY\b', 'cluster by', processed_sql, flags=re.IGNORECASE)
            processed_sql = re.sub(r'\bDISTRIBUTE\s+BY\b', 'distribute by', processed_sql, flags=re.IGNORECASE)
        else:  # capitalize
            processed_sql = re.sub(r'\bCLUSTER\s+BY\b', 'Cluster By', processed_sql, flags=re.IGNORECASE)
            processed_sql = re.sub(r'\bDISTRIBUTE\s+BY\b', 'Distribute By', processed_sql, flags=re.IGNORECASE)

        # 使用基础格式化
        formatted = _call_formatter(processed_sql, keyword_case)

        # 清理末尾分号
        lines = formatted.split('\n')
        while lines and (not lines[-1].strip() or lines[-1].strip() == ';'):
            lines.pop()

        return '\n'.join(lines)

    def _process_basic_transform(self, sql: str, keyword_case: str) -> str:
        """
        处理基础转换（PIVOT/UNPIVOT/TRANSFORM）

        占位实现，后续可以扩展
        """
        # 标准化关键字
        result = sql

        if keyword_case == 'upper':
            result = re.sub(r'\bPIVOT\b', 'PIVOT', result, flags=re.IGNORECASE)
            result = re.sub(r'\bUNPIVOT\b', 'UNPIVOT', result, flags=re.IGNORECASE)
            result = re.sub(r'\bTRANSFORM\b', 'TRANSFORM', result, flags=re.IGNORECASE)
        elif keyword_case == 'lower':
            result = re.sub(r'\bPIVOT\b', 'pivot', result, flags=re.IGNORECASE)
            result = re.sub(r'\bUNPIVOT\b', 'unpivot', result, flags=re.IGNORECASE)
            result = re.sub(r'\bTRANSFORM\b', 'transform', result, flags=re.IGNORECASE)

        # 使用基础格式化
        return _call_formatter(result, keyword_case)

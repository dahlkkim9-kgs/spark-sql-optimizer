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
            # 直接格式化后续子句
            formatted_clauses = self._format_remaining_clauses(remaining_clauses, keyword_case)
            result += '\n' + formatted_clauses.strip()

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
        - 函数参数可换行，括号对齐
        """
        # 标准化关键字
        lv = lateral_view.strip()

        # 解析 LATERAL VIEW 组件（在大小写转换之前）
        # 模式: LATERAL VIEW [OUTER] function(...) table_alias AS column_aliases
        # 使用括号计数来匹配跨行的括号内容
        lateral_view_kw = 'LATERAL VIEW'
        outer_kw = ''
        function_name = None
        function_args = None
        table_alias = None
        as_kw = 'AS'
        column_aliases = None

        # 解析步骤
        remaining = lv
        paren_depth = 0
        i = 0

        # 1. 提取 LATERAL VIEW [OUTER]
        lv_upper = remaining.upper()
        if lv_upper.startswith('LATERAL VIEW'):
            i = len('LATERAL VIEW')
            remaining = remaining[i:].lstrip()

            # 检查 OUTER
            if remaining.upper().startswith('OUTER'):
                outer_kw = 'OUTER'
                # 提取实际的大小写
                outer_match = re.match(r'\s*(OUTER|outer|Outer)\s*', remaining)
                if outer_match:
                    outer_kw = outer_match.group(1)
                remaining = remaining[len(outer_kw):].lstrip()

        # 2. 提取函数名 (EXPLODE/JSON_TUPLE/等)
        func_match = re.match(r'(\w+)', remaining)
        if func_match:
            function_name = func_match.group(1)
            remaining = remaining[len(function_name):].lstrip()

        # 3. 提取函数参数（使用括号计数）
        if remaining.startswith('('):
            paren_depth = 0
            arg_start = 0
            for j, char in enumerate(remaining):
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                    if paren_depth == 0:
                        function_args = remaining[:j+1]
                        remaining = remaining[j+1:].lstrip()
                        break
            else:
                # 没有找到闭合括号，使用整个剩余部分
                function_args = remaining
                remaining = ''

        # 4. 提取表别名
        alias_match = re.match(r'(\w+)', remaining)
        if alias_match:
            table_alias = alias_match.group(1)
            remaining = remaining[len(table_alias):].lstrip()

        # 5. 提取 AS 和列别名
        if remaining.upper().startswith('AS'):
            as_match = re.match(r'(AS|as|As)\s+(.+)', remaining, re.IGNORECASE)
            if as_match:
                as_kw = as_match.group(1)
                column_aliases = as_match.group(2).strip()

        # 如果解析成功，组装结果
        if function_name and function_args and table_alias:
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

            # 格式化函数参数（处理多行和缩进）
            formatted_args = self._format_function_args(function_args)

            # 组装
            result = f"{lateral_view_kw}{outer_kw} {function_name}{formatted_args} {table_alias} {as_kw} {column_aliases}"
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

    def _format_function_args(self, args: str) -> str:
        """
        格式化函数参数，确保括号对齐

        规则:
        - 如果参数简单（单行且较短），保持原样
        - 如果参数跨行，确保闭合括号与开括号对齐
        """
        args = args.strip()

        # 如果没有括号，直接返回
        if not (args.startswith('(') and args.endswith(')')):
            return args

        # 检查参数是否跨行
        if '\n' not in args:
            # 单行参数，检查长度
            inner = args[1:-1].strip()
            if len(inner) < 60:
                return args  # 短参数保持单行

        # 多行参数或长参数，需要格式化
        lines = args.split('\n')
        if len(lines) == 1:
            # 单行但很长的参数，考虑换行
            inner = args[1:-1].strip()
            return f'(\n    {inner}\n)'
        else:
            # 多行参数，确保括号对齐
            # 第一行是开括号
            result = [lines[0]]
            # 中间行保持原样（但去除每行的前导空格，然后添加统一缩进）
            for line in lines[1:-1]:
                stripped = line.strip()
                if stripped:
                    result.append(f'    {stripped}')
                else:
                    result.append('')
            # 最后一行是闭括号，与开括号对齐
            last_line = lines[-1].strip()
            if last_line == ')':
                result.append(')')
            else:
                result.append(f'    {last_line}')
            return '\n'.join(result)

    def _format_remaining_clauses(self, clauses: str, keyword_case: str) -> str:
        """
        格式化后续子句（GROUP BY, HAVING, ORDER BY, LIMIT 等）

        简单的格式化规则：
        - 关键字独占一行或与第一列同行（取决于长度）
        - 多列时，每列独占一行并使用逗号前缀
        - 保留原始的多行格式（如果原始是多行）
        """
        clauses = clauses.strip()
        # 检查原始是否是多行格式
        is_multiline = '\n' in clauses

        # 转换关键字大小写
        if keyword_case == 'upper':
            clauses = re.sub(r'\bGROUP\s+BY\b', 'GROUP BY', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bHAVING\b', 'HAVING', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bORDER\s+BY\b', 'ORDER BY', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bLIMIT\b', 'LIMIT', clauses, flags=re.IGNORECASE)
        elif keyword_case == 'lower':
            clauses = re.sub(r'\bGROUP\s+BY\b', 'group by', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bHAVING\b', 'having', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bORDER\s+BY\b', 'order by', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bLIMIT\b', 'limit', clauses, flags=re.IGNORECASE)
        else:  # capitalize
            clauses = re.sub(r'\bGROUP\s+BY\b', 'Group By', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bHAVING\b', 'Having', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bORDER\s+BY\b', 'Order By', clauses, flags=re.IGNORECASE)
            clauses = re.sub(r'\bLIMIT\b', 'Limit', clauses, flags=re.IGNORECASE)

        # 分解各个子句（GROUP BY, HAVING, ORDER BY, LIMIT）
        # 使用正则来分割子句
        pattern = r'\b(GROUP BY|HAVING|ORDER BY|LIMIT)\b'
        parts = re.split(pattern, clauses, flags=re.IGNORECASE)

        formatted = []
        i = 1
        while i < len(parts):
            keyword = parts[i].upper()
            # 转换关键字大小写
            if keyword_case == 'upper':
                pass  # 已经是大写
            elif keyword_case == 'lower':
                keyword = keyword.lower()
            else:  # capitalize
                keyword = keyword.capitalize()
                if keyword == 'GROUP BY':
                    keyword = 'Group By'
                elif keyword == 'ORDER BY':
                    keyword = 'Order By'

            # 获取内容（直到下一个关键字或结尾）
            content = ''
            if i + 1 < len(parts):
                content = parts[i + 1].strip()

            # 格式化这个子句
            if keyword in ('GROUP BY', 'ORDER BY'):
                # 处理 GROUP BY / ORDER BY（多列可能换行）
                # 检查原始内容是否是多行格式
                original_content_part = None
                for j in range(i - 1, len(parts) - 1, 2):
                    if parts[j].upper() == keyword and j + 1 < len(parts):
                        original_content_part = parts[j + 1]
                        break

                # 如果原始是多行且有逗号，保留多行格式
                if original_content_part and '\n' in original_content_part and ',' in content:
                    columns = [c.strip() for c in content.split(',')]
                    formatted.append(keyword)
                    for j, col in enumerate(columns):
                        if j == 0:
                            formatted.append(f'    {col}')
                        else:
                            formatted.append(f'     , {col}')
                elif ',' in content:
                    # 单行格式但有逗号，也分成多行（更易读）
                    columns = [c.strip() for c in content.split(',')]
                    formatted.append(keyword)
                    for j, col in enumerate(columns):
                        if j == 0:
                            formatted.append(f'    {col}')
                        else:
                            formatted.append(f'     , {col}')
                else:
                    formatted.append(f'{keyword} {content}')
            elif keyword == 'HAVING':
                formatted.append(f'{keyword} {content}')
            elif keyword == 'LIMIT':
                formatted.append(f'{keyword} {content}')

            i += 2

        return '\n'.join(formatted)

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

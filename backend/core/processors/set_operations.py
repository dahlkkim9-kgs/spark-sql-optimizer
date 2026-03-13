# backend/core/processors/set_operations.py
"""集合操作处理器 - 支持 UNION/INTERSECT/EXCEPT/MINUS"""
import re
from typing import List, Literal
from .base_processor import BaseProcessor


class SetOperationsProcessor(BaseProcessor):
    """集合操作处理器 - 支持 UNION/INTERSECT/EXCEPT/MINUS"""

    def __init__(self):
        super().__init__()
        # 按优先级排序的模式列表（UNION ALL 必须在 UNION 之前）
        self.patterns = [
            ('UNION ALL', re.compile(r'\bUNION\s+ALL\b', re.IGNORECASE)),
            ('UNION', re.compile(r'\bUNION\b(?!\s+ALL)', re.IGNORECASE)),
            ('INTERSECT', re.compile(r'\bINTERSECT\b', re.IGNORECASE)),
            ('EXCEPT', re.compile(r'\bEXCEPT\b', re.IGNORECASE)),
            ('MINUS', re.compile(r'\bMINUS\b', re.IGNORECASE))
        ]

    def can_process(self, sql: str) -> bool:
        """检查 SQL 是否包含集合操作"""
        for name, pattern in self.patterns:
            if pattern.search(sql):
                return True
        return False

    def process(self, sql: str, keyword_case: Literal['upper', 'lower', 'capitalize'] = 'upper') -> str:
        """处理包含集合操作的 SQL"""
        # 去除首尾空白
        sql = sql.strip()

        # 分割集合操作（智能处理括号）
        segments = self._split_by_set_operations(sql)

        # 格式化每个 SELECT 语句
        formatted_segments = []
        for i, segment in enumerate(segments):
            if i % 2 == 0:  # SELECT 语句或括号包裹的子查询
                formatted = self._format_segment(segment, keyword_case)
                formatted_segments.append(formatted)
            else:  # 集合操作符
                formatted_segments.append(segment.upper())

        # 用换行连接
        return '\n'.join(formatted_segments)

    def _format_segment(self, segment: str, keyword_case: str) -> str:
        """格式化单个段落（可能是 SELECT 语句或括号包裹的子查询）"""
        segment = segment.strip()

        # 检查是否是括号包裹的子查询
        if segment.startswith('(') and segment.endswith(')'):
            # 移除外层括号
            inner = segment[1:-1].strip()

            # 检查内部是否有集合操作
            if self.can_process(inner):
                # 递归处理内部的集合操作
                inner_formatted = self.process(inner, keyword_case)
                return f'({inner_formatted})'
            else:
                # 普通子查询，直接格式化
                formatted = format_sql_v4_fixed(inner, keyword_case=keyword_case)
                formatted = self._clean_formatted_select(formatted)
                return f'({formatted})'
        else:
            # 普通 SELECT 语句
            formatted = format_sql_v4_fixed(segment, keyword_case=keyword_case)
            return self._clean_formatted_select(formatted)

    def _clean_formatted_select(self, formatted: str) -> str:
        """清理 format_sql_v4_fixed 的输出，移除分号和多余空行"""
        # 移除末尾的分号和周围空行
        lines = formatted.split('\n')
        # 移除最后的空行和分号行
        while lines and (not lines[-1].strip() or lines[-1].strip() == ';'):
            lines.pop()

        # 移除开头的空行
        while lines and not lines[0].strip():
            lines.pop(0)

        return '\n'.join(lines)

    def _split_by_set_operations(self, sql: str) -> List[str]:
        """按集合操作符分割 SQL（考虑括号嵌套）"""
        segments = []
        current = ""
        i = 0
        paren_depth = 0

        while i < len(sql):
            char = sql[i]

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

            # 只在顶层（括号外）检查集合操作符
            if paren_depth == 0:
                matched = False
                for name, pattern in self.patterns:
                    match = pattern.match(sql, pos=i)
                    if match:
                        # 添加当前累积的内容
                        if current.strip():
                            segments.append(current.strip())
                        # 添加操作符
                        segments.append(name)
                        # 跳过匹配的部分
                        i = match.end()
                        current = ""
                        matched = True
                        break

                if not matched:
                    current += char
                    i += 1
            else:
                # 在括号内，直接添加字符
                current += char
                i += 1

        # 添加最后一段
        if current.strip():
            segments.append(current.strip())

        return segments

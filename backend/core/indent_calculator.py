"""
统一缩进计算模块

提供统一的缩进计算逻辑，确保所有嵌套内容都遵循「开括号位置 + 1」的对齐规则。

核心规则：
- 括号内内容缩进：开括号位置 + 1
- 闭括号对齐：与对应的开括号对齐
"""

import re
from typing import List, Tuple, Optional


class IndentCalculator:
    """统一缩进计算器"""

    @staticmethod
    def find_open_paren_pos(line: str) -> int:
        """
        查找行中最后一个开括号的位置

        Args:
            line: 要分析的行

        Returns:
            开括号的列位置（从 0 开始），如果找不到返回 -1
        """
        pos = line.rfind('(')
        return pos if pos >= 0 else -1

    @staticmethod
    def calc_open_paren_plus_1(open_paren_pos: int) -> int:
        """
        计算开括号位置 + 1 的缩进

        Args:
            open_paren_pos: 开括号的列位置

        Returns:
            内容应该缩进到的列位置
        """
        return open_paren_pos + 1

    @staticmethod
    def calc_close_paren_indent(open_paren_pos: int) -> int:
        """
        计算闭括号的缩进位置（与开括号对齐）

        Args:
            open_paren_pos: 开括号的列位置

        Returns:
            闭括号应该缩进到的列位置
        """
        return open_paren_pos

    @staticmethod
    def make_indent(col_pos: int) -> str:
        """
        生成指定列位置的缩进字符串

        Args:
            col_pos: 列位置

        Returns:
            由空格组成的缩进字符串
        """
        return ' ' * col_pos

    @staticmethod
    def format_paren_content(
        content: str,
        open_paren_pos: int,
        base_context: str = ""
    ) -> str:
        """
        格式化括号内内容，使用「开括号 + 1」规则

        Args:
            content: 括号内的内容（可能包含换行）
            open_paren_pos: 开括号在上下文行中的列位置
            base_context: 可选的基础上下文（用于日志/调试）

        Returns:
            格式化后的内容，包含开括号、缩进的内容、闭括号
        """
        content_indent = IndentCalculator.calc_open_paren_plus_1(open_paren_pos)
        close_indent = IndentCalculator.calc_close_paren_indent(open_paren_pos)

        content_str = IndentCalculator.make_indent(content_indent)
        close_str = IndentCalculator.make_indent(close_indent)

        # 分割内容为多行
        lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped:
                lines.append(content_str + stripped)
            else:
                lines.append('')

        # 组装结果
        result = ['('] + lines + [close_str + ')']
        return '\n'.join(result)


class ParenContentFormatter:
    """
    括号内容格式化器

    处理括号内的 AND/OR 条件，按照「开括号 + 1」规则缩进
    """

    # 正则模式
    AND_PATTERN = re.compile(r'\bAND\b', re.IGNORECASE)
    OR_PATTERN = re.compile(r'\bOR\b', re.IGNORECASE)

    @staticmethod
    def protect_strings(s: str) -> Tuple[str, List[str]]:
        """保护字符串字面量"""
        markers = []
        def protect(match):
            placeholder = f'__STRING_{len(markers)}__'
            markers.append(match.group(0))
            return placeholder
        protected = re.sub(r"('[^']*')", protect, s)
        return protected, markers

    @staticmethod
    def restore_strings(text: str, markers: List[str]) -> str:
        """恢复字符串字面量"""
        for idx, marker in enumerate(markers):
            text = text.replace(f'__STRING_{idx}__', marker)
        return text

    @staticmethod
    def split_by_logical_op(content: str, op: str) -> List[str]:
        """
        按逻辑运算符分割内容（考虑括号嵌套）

        Args:
            content: 要分割的内容（字符串已保护）
            op: 运算符（'AND' 或 'OR'）

        Returns:
            分割后的部分列表
        """
        parts = []
        current = ''
        depth = 0
        i = 0
        op_len = len(op)

        while i < len(content):
            char = content[i]

            if char == '(':
                depth += 1
                current += char
                i += 1
            elif char == ')':
                depth -= 1
                current += char
                i += 1
            elif depth == 0 and i + op_len <= len(content) and content[i:i+op_len].upper() == op:
                # 检查边界（确保不是单词的一部分）
                before_ok = (i == 0 or not content[i-1].isalnum() and content[i-1] != '_')
                after_ok = (i + op_len >= len(content) or not content[i+op_len].isalnum() and content[i+op_len] != '_')
                if before_ok and after_ok:
                    parts.append(current.strip())
                    current = ''
                    i += op_len
                    continue
            else:
                current += char
                i += 1

        if current.strip():
            parts.append(current.strip())

        return parts if parts else [content]

    @classmethod
    def format_paren_with_logical_ops(
        cls,
        paren_content: str,
        open_paren_pos: int
    ) -> str:
        """
        格式化包含 AND/OR 的括号内容

        Args:
            paren_content: 括号内的内容
            open_paren_pos: 开括号的列位置

        Returns:
            格式化后的多行字符串
        """
        # 计算缩进
        content_indent_pos = IndentCalculator.calc_open_paren_plus_1(open_paren_pos)
        close_indent_pos = IndentCalculator.calc_close_paren_indent(open_paren_pos)

        content_indent = IndentCalculator.make_indent(content_indent_pos)
        close_indent = IndentCalculator.make_indent(close_indent_pos)

        # 保护字符串
        protected, string_markers = cls.protect_strings(paren_content)

        # 首先尝试按 OR 分割
        or_parts = cls.split_by_logical_op(protected, 'OR')

        if len(or_parts) > 1:
            lines = ['(']
            for i, part in enumerate(or_parts):
                restored = cls.restore_strings(part.strip(), string_markers)
                if i == 0:
                    lines.append(content_indent + restored)
                else:
                    lines.append(content_indent + 'OR ' + restored)
            lines.append(close_indent + ')')
            return '\n'.join(lines)

        # 没有OR，检查 AND
        and_parts = cls.split_by_logical_op(protected, 'AND')
        if len(and_parts) > 1:
            lines = ['(']
            for i, part in enumerate(and_parts):
                restored = cls.restore_strings(part.strip(), string_markers)
                if i == 0:
                    lines.append(content_indent + restored)
                else:
                    lines.append(content_indent + 'AND ' + restored)
            lines.append(close_indent + ')')
            return '\n'.join(lines)

        # 没有需要分割的逻辑运算符，返回单行
        return '(' + paren_content + ')'


def calculate_indent_for_context(context_line: str, keyword: str = "") -> int:
    """
    根据上下文行计算缩进位置

    找到指定关键字后的开括号位置，返回「开括号 + 1」的缩进值

    Args:
        context_line: 上下文行（如 "WHERE (a=1" 或 "FROM ("）
        keyword: 可选的关键字（如 "WHERE", "FROM"），用于更精确的定位

    Returns:
        内容应该缩进的列位置（开括号位置 + 1）
    """
    # 查找开括号位置
    open_paren_pos = IndentCalculator.find_open_paren_pos(context_line)

    if open_paren_pos == -1:
        # 没有找到括号，返回默认值（关键字后 + 固定偏移）
        if keyword:
            keyword_pos = context_line.upper().find(keyword.upper())
            if keyword_pos != -1:
                return keyword_pos + len(keyword) + 1
        return 4  # 默认 4 个空格

    # 返回开括号 + 1
    return IndentCalculator.calc_open_paren_plus_1(open_paren_pos)

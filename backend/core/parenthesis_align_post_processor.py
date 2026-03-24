# -*- coding: utf-8 -*-
"""括号对齐后处理器

只调整括号缩进，不添加或删除括号
复用 V4 的 IndentContext 进行缩进计算
"""
from typing import List, Tuple

try:
    from .indent_context import IndentContext
    from .sql_utils import find_matching_paren
except ImportError:
    from indent_context import IndentContext
    from sql_utils import find_matching_paren


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

        遵循 V4 的 "开括号+1" 规则：
        - 开括号位置 = len(prefix)
        - 内容缩进 = 开括号位置 + 1
        - 闭括号缩进 = 开括号位置

        Args:
            sql: sqlglot 格式化后的 SQL

        Returns:
            括号缩进调整后的 SQL
        """
        lines = sql.split('\n')
        result = []
        paren_stack = []  # 存储 (开括号位置, 内容缩进)

        for line in lines:
            analysis = self._analyze_line_parens(line)

            # 处理闭括号行
            if analysis['has_close_paren'] and not analysis['has_open_paren']:
                if paren_stack:
                    open_pos, _ = paren_stack.pop()
                    # 闭括号与开括号对齐
                    result.append(' ' * open_pos + ')')
                    continue

            # 处理开括号行
            if analysis['has_open_paren']:
                # 计算开括号绝对位置
                # prefix 包含前导空格，需要使用整行的 prefix
                prefix = analysis['prefix']  # 已包含原始缩进
                open_pos = len(prefix)
                content_indent = open_pos + 1

                # 压栈
                paren_stack.append((open_pos, content_indent))

                # 输出开括号行
                result.append(line.rstrip())
                continue

            # 处理内容行（有活动括号上下文时）
            if paren_stack:
                _, content_indent = paren_stack[-1]
                stripped = line.lstrip()
                if stripped:  # 非空行
                    result.append(' ' * content_indent + stripped)
                    continue

            # 默认：保持原样
            result.append(line)

        return '\n'.join(result)
        # lines = sql.split('\n')
        # result = []
        # paren_stack = []  # 存储 (开括号位置, 内容缩进)
        #
        # for line in lines:
        #     analysis = self._analyze_line_parens(line)
        #
        #     # 处理闭括号行
        #     if analysis['has_close_paren'] and not analysis['has_open_paren']:
        #         if paren_stack:
        #             open_pos, _ = paren_stack.pop()
        #             # 闭括号与开括号对齐
        #             result.append(' ' * open_pos + ')')
        #             continue
        #
        #     # 处理开括号行
        #     if analysis['has_open_paren']:
        #         # 计算开括号绝对位置
        #         prefix = analysis['prefix']
        #         open_pos = analysis['base_indent'] + len(prefix)
        #         content_indent = open_pos + 1
        #
        #         # 压栈
        #         paren_stack.append((open_pos, content_indent))
        #
        #         # 输出开括号行
        #         result.append(line.rstrip())
        #         continue
        #
        #     # 处理内容行（有活动括号上下文时）
        #     if paren_stack:
        #         _, content_indent = paren_stack[-1]
        #         stripped = line.lstrip()
        #         if stripped:  # 非空行
        #             result.append(' ' * content_indent + stripped)
        #             continue
        #
        #     # 默认：保持原样
        #     result.append(line)
        #
        # return '\n'.join(result)

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

        Note:
            此方法目前已禁用，因为 process() 方法直接返回原 SQL。
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
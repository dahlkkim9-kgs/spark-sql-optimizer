"""缩进上下文类，用于追踪 SQL 格式化过程中的累积缩进

遵循"开括号+1"规则：
- 对于任意行 `prefix (`
- 开括号位置 = len(prefix)
- 内容缩进 = len(prefix) + 1
- 闭括号缩进 = len(prefix)
"""

from typing import List


class IndentContext:
    """缩进上下文，跟踪当前累积缩进和括号栈"""

    def __init__(self, base_indent: int = 0):
        """初始化缩进上下文

        Args:
            base_indent: 当前累积的基础缩进（空格数）
        """
        self.base_indent = base_indent
        self.stack: List[int] = []  # 括号栈，记录每层的开括号位置

    def push_paren(self, prefix: str) -> int:
        """压入一层括号，记录开括号位置

        Args:
            prefix: 开括号前的内容（如 "FROM ", "INNER JOIN "）

        Returns:
            内容应该缩进到的空格数

        Example:
            ctx = IndentContext(base_indent=0)
            indent = ctx.push_paren("FROM ")  # 返回 6
            # 对于 "FROM (", 开括号在位置 5，内容缩进到 6
        """
        # 计算当前行的开括号绝对位置
        paren_pos = self.base_indent + len(prefix)
        self.stack.append(paren_pos)
        # 内容缩进 = 开括号位置 + 1
        return paren_pos + 1

    def pop_paren(self) -> int:
        """弹出一层括号

        Returns:
            闭括号应该缩进到的空格数（与开括号对齐）

        Example:
            ctx = IndentContext(base_indent=0)
            ctx.push_paren("FROM ")  # 开括号在位置 5
            close_indent = ctx.pop_paren()  # 返回 5
        """
        if self.stack:
            return self.stack.pop()
        return self.base_indent

    def get_content_indent(self, prefix: str) -> int:
        """获取新括号的内容缩进（不压栈）

        Args:
            prefix: 开括号前的内容

        Returns:
            内容应该缩进到的空格数
        """
        return self.base_indent + len(prefix) + 1

    def get_close_indent(self, prefix: str) -> int:
        """获取闭括号缩进（不弹栈）

        Args:
            prefix: 开括号前的内容

        Returns:
            闭括号应该缩进到的空格数
        """
        return self.base_indent + len(prefix)

    def with_base_indent(self, new_base: int) -> 'IndentContext':
        """创建带有新基础缩进的上下文副本

        Args:
            new_base: 新的基础缩进值（绝对值）

        Returns:
            新的 IndentContext 实例

        Example:
            ctx = IndentContext(base_indent=0)
            new_ctx = ctx.with_base_indent(6)  # 新基础缩进为 6
        """
        new_ctx = IndentContext(new_base)
        # 复制括号栈（共享引用）
        new_ctx.stack = self.stack.copy()
        return new_ctx

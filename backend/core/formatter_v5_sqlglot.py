# -*- coding: utf-8 -*-
"""
SQL Formatter V5 - 基于 sqlglot AST 解析
结合 v4 的格式化风格
"""
from typing import Optional, List
from sqlglot import parse, exp
from sqlglot.dialects import Spark

# 共享工具和格式化器导入
try:
    from .sql_utils import split_by_semicolon
    from .formatter_v4_fixed import format_sql_v4_fixed
    from .parenthesis_align_post_processor import ParenthesisAlignPostProcessor
except ImportError:
    from sql_utils import split_by_semicolon
    from formatter_v4_fixed import format_sql_v4_fixed
    from parenthesis_align_post_processor import ParenthesisAlignPostProcessor


# 常量定义
DOLLAR_PLACEHOLDER = "___DOLLAR_SIGN_PLACEHOLDER___"


class SQLFormatterV5:
    """基于 sqlglot 的 SQL 格式化器"""

    # 类常量
    DOLLAR_PLACEHOLDER = DOLLAR_PLACEHOLDER

    def __init__(self, indent_spaces: int = 4):
        self.indent_spaces = indent_spaces

    def _log(self, step: str, details: str = "") -> None:
        """统一的日志输出方法"""
        msg = f"[V5格式化器] {step}"
        if details:
            msg += f": {details}"
        print(msg)

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

        注意：
        - 只处理最外层 SELECT 的列，子查询保持原样
        - 带注释的列保持原样（不重新格式化）
        """
        lines = sql.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检测 SELECT 子句（包括 SELECT DISTINCT, SELECT ALL 等）
            if stripped.startswith('SELECT'):
                # 获取缩进
                indent = line[:line.index('SELECT')]

                # 提取 SELECT 修饰符（DISTINCT, ALL 等）
                select_modifier = ""
                if " DISTINCT" in stripped:
                    select_modifier = " DISTINCT"
                elif " ALL" in stripped:
                    select_modifier = " ALL"

                # 查找 SELECT 后面的列
                i += 1
                columns = []  # 存储列信息 (type, content, has_comment)

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

                    # 检查是否包含注释
                    has_comment = ('/*' in col_line or '--' in col_line)

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
                        columns.append(('subquery', '\n'.join(sub_lines), has_comment))
                        continue

                    # 普通列
                    # 移除结尾的逗号
                    col_name = col_stripped.rstrip(',').strip()
                    if col_name:
                        columns.append(('simple', col_name, has_comment))
                    i += 1

                # 格式化列
                if columns:
                    # 第一列
                    if columns[0][0] == 'simple' and not columns[0][2]:
                        result.append(f"{indent}SELECT{select_modifier} {columns[0][1]}")
                    elif columns[0][0] == 'simple':
                        # 带注释的列，保持原样
                        result.append(f"{indent}SELECT{select_modifier}")
                        result.append(lines[1])  # 原始第一列行
                    else:  # subquery
                        result.append(f"{indent}SELECT{select_modifier}")
                        result.append(columns[0][1])

                    # 后续列
                    for idx, (col_type, col_content, has_comment) in enumerate(columns[1:], 1):
                        if col_type == 'simple' and not has_comment:
                            result.append(f"{indent}     , {col_content}")
                        elif col_type == 'simple':
                            # 带注释的列，保持原样
                            # 需要找到原始行
                            # 这里简化处理：直接使用列内容（带逗号）
                            result.append(f"{indent}     {col_content},")
                        else:  # subquery
                            result.append(f"{indent}     ,")
                            result.append(col_content)
                else:
                    result.append(f"{indent}SELECT{select_modifier}")

                # 继续处理（i 已经指向下一行）
                continue

            result.append(line)
            i += 1

        return '\n'.join(result)

    def _apply_v4_full_style(self, sql: str) -> str:
        """应用完整的 V4 风格后处理

        处理：
        1. 修复 WHERE 条件（应该在同一行，如果不太长）
        2. 统一子查询缩进（1 空格递增）
        3. 添加结尾分号
        """
        lines = sql.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检测 WHERE 子句后跟条件（在不同行）
            if stripped == 'WHERE' and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # 如果下一行是条件（不是关键字），合并到一行
                if next_line and not any(next_line.startswith(kw) for kw in ['SELECT', 'FROM', 'WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT', 'JOIN', 'ON', 'AND', 'OR']):
                    result.append('WHERE ' + next_line)
                    i += 2
                    continue

            # 处理缩进
            if (stripped.startswith('FROM') or
                stripped.startswith('WHERE') or
                stripped.startswith('INNER JOIN') or
                stripped.startswith('LEFT JOIN') or
                stripped.startswith('RIGHT JOIN') or
                stripped.startswith('FULL JOIN') or
                stripped.startswith('CROSS JOIN') or
                stripped.startswith('ORDER BY') or
                stripped.startswith('GROUP BY') or
                stripped.startswith('HAVING') or
                stripped.startswith('LIMIT')):
                # 主子句顶格
                result.append(stripped)
            elif stripped.startswith('ON') or stripped.startswith('AND') or stripped.startswith('OR'):
                # ON/AND/OR 缩进 2 空格
                result.append('  ' + stripped)
            elif stripped.startswith('SELECT'):
                # 检查是否是子查询
                if result and result[-1].strip() == '(':
                    # 子查询的 SELECT，缩进 1 空格
                    result.append(' ' + stripped)
                elif result and result[-1].strip().endswith('('):
                    # 也可能是子查询
                    result.append(' ' + stripped)
                else:
                    result.append(stripped)
            else:
                # 保持原有缩进，但规范化（子查询内容）
                if stripped:
                    current_indent = len(line) - len(line.lstrip())
                    # 如果是子查询内容（缩进 > 0），规范化为 1 空格递增
                    if current_indent > 0 and result:
                        # 获取上一层的缩进
                        last_indent = len(result[-1]) - len(result[-1].lstrip()) if result[-1].strip() else 0
                        # 如果当前缩进与上一行相差较大，规范化
                        if current_indent - last_indent > 2:
                            result.append(' ' * (last_indent + 1) + stripped)
                        else:
                            result.append(line)
                    else:
                        result.append(line)
                else:
                    result.append(line)

            i += 1

        # 添加结尾分号
        formatted = '\n'.join(result)
        if formatted and not formatted.rstrip().endswith(';'):
            formatted = formatted + '\n;'

        return formatted

    def _protect_line_comments(self, sql: str) -> tuple:
        """保护行内 -- 注释

        1. 查找所有 -- 注释（不包括字符串内的 --）
        2. 替换为占位符 __COMMENT_N__
        3. 返回 (替换后的SQL, 注释列表)
        """
        comments = []
        result = []
        i = 0

        while i < len(sql):
            char = sql[i]

            # 检测行内注释 --
            if char == '-' and i + 1 < len(sql) and sql[i + 1] == '-':
                # 检查是否在字符串内
                in_string = False

                # 简单检查：向前查找字符串开始
                for j in range(i - 1, -1, -1):
                    if sql[j] in ('"', "'"):
                        # 找到引号，检查是否转义
                        if j > 0 and sql[j - 1] != '\\':
                            in_string = not in_string

                if not in_string:
                    # 找到注释结束位置（行尾）
                    comment_start = i
                    comment_end = i + 2

                    while comment_end < len(sql) and sql[comment_end] not in ('\n', '\r'):
                        comment_end += 1

                    # 提取注释内容
                    comment = sql[comment_start:comment_end].strip()
                    comments.append(comment)

                    # 替换为占位符
                    placeholder = f" __COMMENT_{len(comments) - 1}__ "
                    result.append(placeholder)

                    # 跳到行尾
                    i = comment_end
                    continue

            result.append(char)
            i += 1

        return ''.join(result), comments

    def _restore_line_comments(self, sql: str, comments: list) -> str:
        """恢复 -- 注释格式

        1. 查找所有占位符 __COMMENT_N__
        2. 替换回原 -- 注释
        3. 同时把 /* */ 格式改回 -- 格式（如果 sqlglot 转换了）
        """
        result = sql

        # 首先恢复占位符
        for i, comment in enumerate(comments):
            placeholder = f" __COMMENT_{i}__ "
            if placeholder in result:
                result = result.replace(placeholder, f" {comment} ")

        # 然后把 /* */ 改回 -- 格式（如果 sqlglot 转换了）
        import re
        # 简单处理：单行 /* comment */ 改为 -- comment
        result = re.sub(r'/\* (.*?) \*/', r'-- \1', result)

        return result

    def _escape_dollar_signs(self, sql: str) -> tuple:
        """临时转义 $ 符号以绕过 sqlglot 解析限制

        Spark SQL 使用 $ 进行变量替换（如 table_$date）
        sqlglot 无法正确解析这种语法，需要临时转义
        """
        escaped = sql.replace('$', self.DOLLAR_PLACEHOLDER)
        return escaped, self.DOLLAR_PLACEHOLDER

    def _unescape_dollar_signs(self, sql: str) -> str:
        """恢复 $ 符号"""
        return sql.replace(self.DOLLAR_PLACEHOLDER, '$')

    def format(self, sql: str, dialect: str = "spark") -> str:
        """格式化 SQL

        策略：使用 sqlglot 解析（确保语法正确性），然后用 V4 格式化

        Args:
            sql: 原始 SQL（支持多语句，用分号分隔）
            dialect: SQL 方言 (默认 spark)

        Returns:
            格式化后的 SQL
        """
        # 临时转义 $ 符号
        escaped_sql, _ = self._escape_dollar_signs(sql)

        # 首先尝试整体解析（仅用于验证语法）
        try:
            # 解析为 AST（验证语法正确性）
            asts = parse(escaped_sql, dialect=dialect, read=dialect)

            if not asts:
                return sql

            # 语法正确，直接使用 V4 格式化（保持风格一致）
            # 分割语句
            statements = split_by_semicolon(sql)

            formatted_statements = []
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt:
                    continue

                # 确保以分号结尾
                if not stmt.endswith(';'):
                    stmt += ';'

                # 使用 V4 格式化
                formatted = format_sql_v4_fixed(stmt, **{'indent': self.indent_spaces})
                formatted_statements.append(formatted)

            # 用空行分隔多个语句
            return '\n\n'.join(formatted_statements)

        except Exception as e:
            # 解析失败，尝试逐语句混合解析
            self._log("整体解析失败", f"{type(e).__name__}，尝试逐语句混合解析")

            # 使用共享的语句分割函数（更高效，支持字符串处理）
            statements = split_by_semicolon(sql)

            # 逐语句尝试解析
            formatted_statements = []

            for i, stmt in enumerate(statements):
                stmt = stmt.strip()
                if not stmt:
                    continue

                # 移除结尾分号
                if stmt.endswith(';'):
                    stmt = stmt[:-1].strip()

                try:
                    # 尝试用 sqlglot 解析验证语法
                    escaped_stmt, _ = self._escape_dollar_signs(stmt)
                    asts = parse(escaped_stmt, dialect=dialect, read=dialect)
                    if asts:
                        # 语法正确，使用 V4 格式化
                        formatted = format_sql_v4_fixed(stmt + ';', **{'indent': self.indent_spaces})
                        formatted_statements.append(formatted)
                        self._log(f"语句 {i+1}/{len(statements)}", "语法验证通过，使用 V4 格式化")
                    else:
                        raise ValueError("No AST returned")
                except Exception:
                    # 该语句语法可能有问题，直接用 V4 格式化
                    self._log(f"语句 {i+1}/{len(statements)}", "使用 V4 格式化")
                    formatted = format_sql_v4_fixed(stmt + ';', **{'indent': self.indent_spaces})
                    formatted_statements.append(formatted)

            # 合并所有语句
            result = '\n\n'.join(formatted_statements)
            self._log("混合解析完成", f"{len(statements)} 个语句")
            return result


def format_sql_v5(sql: str, **options) -> str:
    """v5 格式化入口函数"""
    formatter = SQLFormatterV5(
        indent_spaces=options.get('indent', 4)
    )
    return formatter.format(sql)

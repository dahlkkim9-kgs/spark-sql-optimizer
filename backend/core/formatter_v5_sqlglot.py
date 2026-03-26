# -*- coding: utf-8 -*-
"""
SQL Formatter V5 - 基于 sqlglot AST 解析 + V4 列对齐后处理

正确架构：
1. sqlglot 解析并基础格式化
2. 将 /* */ 注释改回 -- 格式
3. V4 列对齐后处理
"""
from typing import Optional
from sqlglot import parse
import re


class SQLFormatterV5:
    """基于 sqlglot 的 SQL 格式化器"""

    def __init__(self, indent_spaces: int = 4):
        self.indent_spaces = indent_spaces

    def _log(self, step: str, details: str = "") -> None:
        """统一的日志输出方法"""
        msg = f"[V5格式化器] {step}"
        if details:
            msg += f": {details}"
        print(msg)

    def _convert_block_comments_to_line_comments(self, sql: str) -> str:
        """将 /* comment */ 格式改回 -- comment

        sqlglot 会把 -- 转换成 /* */，这里改回来

        处理情况：
        - `a, /* comment */` -> `a --comment` (移除注释前的逗号)
        - `a /* comment */` -> `a --comment`
        """
        result = []
        lines = sql.split('\n')

        for line in lines:
            # 查找 /* ... */ 模式
            pattern = r'/\*\s+(.*?)\s+\*/'
            matches = list(re.finditer(pattern, line))

            # 从后往前替换（避免位置偏移）
            new_line = line
            for match in reversed(matches):
                comment_content = match.group(1).strip()
                start = match.start()
                end = match.end()

                # 检查注释前是否有逗号
                before_comment = new_line[:start].rstrip()
                has_comma = before_comment.endswith(',')

                # 替换为 -- 格式
                replacement = f"--{comment_content}"

                # 如果有逗号，移除它
                if has_comma:
                    new_line = before_comment[:-1] + ' ' + replacement + new_line[end:]
                else:
                    new_line = new_line[:start] + replacement + new_line[end:]

            result.append(new_line)

        return '\n'.join(result)

    def _apply_v4_column_style(self, sql: str) -> str:
        """应用 v4 风格的列对齐

        将逗号移到行首，并保持对齐
        """
        lines = sql.split('\n')
        result = []
        in_select = False
        columns = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检测 SELECT 开始
            if stripped.upper().startswith('SELECT'):
                # 提取 SELECT 后面的内容
                parts = stripped.split(None, 1)
                if len(parts) > 1:
                    # SELECT a, b -> 第一列是 a
                    first_col = parts[1].strip()
                    # 移除结尾逗号
                    if first_col.endswith(','):
                        first_col = first_col[:-1].strip()
                    if first_col:
                        columns.append(first_col)
                in_select = True
                continue

            # 检测 FROM/WHERE/GROUP BY 等结束 SELECT 子句
            if in_select and stripped:
                first_word = stripped.split()[0].upper()
                if first_word in ('FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT', 'UNION', 'INTERSECT', 'EXCEPT',
                                 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'):
                    # 输出之前收集的列
                    if columns:
                        for j, col in enumerate(columns):
                            if j == 0:
                                result.append(f"SELECT {col}")
                            else:
                                result.append(f"     , {col}")
                        columns = []
                    in_select = False
                    result.append(line)
                    continue

            # 在 SELECT 子句中，收集列
            if in_select:
                if stripped and not stripped.startswith('--'):
                    # 处理列
                    col = stripped
                    # 移除开头的逗号
                    if col.startswith(','):
                        col = col[1:].strip()
                    # 移除结尾的逗号
                    if col.endswith(','):
                        col = col[:-1].strip()
                    if col:
                        columns.append(col)
                    continue
                elif stripped.startswith('--'):
                    # 注释行，直接输出
                    if columns:
                        for j, col in enumerate(columns):
                            if j == 0:
                                result.append(f"SELECT {col}")
                            else:
                                result.append(f"     , {col}")
                        columns = []
                    result.append(line)
                    continue

            # 输出之前收集的列
            if columns and not in_select:
                for j, col in enumerate(columns):
                    if j == 0:
                        result.append(f"SELECT {col}")
                    else:
                        result.append(f"     , {col}")
                columns = []

            result.append(line)

        # 处理剩余的列
        if columns:
            for j, col in enumerate(columns):
                if j == 0:
                    result.append(f"SELECT {col}")
                else:
                    result.append(f"     , {col}")

        return '\n'.join(result)

    def _escape_dollar_signs(self, sql: str) -> tuple:
        """转义特殊符号（sqlglot 可能误解析）

        转义 $ 符号和 {} 变量语法
        """
        import re
        # 转义 $ 符号
        escaped = re.sub(r'\$', '___DOLLAR___', sql)
        # 转义 {} 变量语法，如 {DATA_DT}
        escaped = re.sub(r'\{([^}]*)\}', r'___BRACE_OPEN___\1___BRACE_CLOSE___', escaped)
        return escaped, sql.count('$') + sql.count('{')

    def _unescape_dollar_signs(self, sql: str) -> str:
        """恢复转义的符号"""
        import re
        # 恢复 {} 变量语法 - 非贪婪匹配任意字符
        sql = re.sub(r'___BRACE_OPEN___(.*?)___BRACE_CLOSE___', r'{\1}', sql)
        # 恢复 $ 符号
        sql = re.sub(r'___DOLLAR___', '$', sql)
        return sql

    def _split_sql_statements(self, sql: str) -> list:
        """分割 SQL 语句

        按分号分割，但忽略字符串和注释中的分号
        """
        statements = []
        current = []
        i = 0

        while i < len(sql):
            char = sql[i]

            # 处理字符串
            if char in ('"', "'"):
                quote = char
                current.append(char)
                i += 1
                while i < len(sql) and sql[i] != quote:
                    if sql[i] == '\\' and i + 1 < len(sql):
                        current.append(sql[i])
                        i += 1
                    current.append(sql[i])
                    i += 1
                if i < len(sql):
                    current.append(sql[i])
                    i += 1
                continue

            # 处理 -- 注释
            if char == '-' and i + 1 < len(sql) and sql[i + 1] == '-':
                while i < len(sql) and sql[i] not in ('\n', '\r'):
                    current.append(sql[i])
                    i += 1
                continue

            # 处理 /* */ 注释
            if char == '/' and i + 1 < len(sql) and sql[i + 1] == '*':
                while i < len(sql) and not (sql[i] == '*' and i + 1 < len(sql) and sql[i + 1] == '/'):
                    current.append(sql[i])
                    i += 1
                if i < len(sql):
                    current.append(sql[i])
                    i += 1
                if i < len(sql):
                    current.append(sql[i])
                    i += 1
                continue

            # 处理分号
            if char == ';':
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue

            current.append(char)
            i += 1

        # 最后一个语句
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)

        return statements

    def format(self, sql: str, dialect: str = "spark") -> str:
        """格式化 SQL

        正确架构：
        1. 分割 SQL 语句
        2. 对每个语句：sqlglot 解析 → 格式化 → 注释转换 → 列对齐
        3. 合并结果

        Args:
            sql: 原始 SQL
            dialect: SQL 方言 (默认 spark)

        Returns:
            格式化后的 SQL
        """
        # Step 1: 分割语句
        statements = self._split_sql_statements(sql)

        if not statements:
            return sql

        # Step 2: 分别格式化每个语句
        formatted_statements = []
        failed_statements = []

        for i, stmt in enumerate(statements):
            try:
                # 转义 $ 符号
                escaped_stmt, _ = self._escape_dollar_signs(stmt)

                # sqlglot 解析并格式化
                asts = parse(escaped_stmt, dialect=dialect, read=dialect)

                if not asts:
                    # sqlglot 无法解析，保留原语句
                    self._log(f"语句 {i+1}", "sqlglot 返回空，保留原语句")
                    formatted_statements.append(stmt)
                    continue

                # 格式化（通常只有一个 AST）
                formatted = []
                for ast in asts:
                    fmt = ast.sql(dialect=dialect, pretty=True, indent=self.indent_spaces)
                    # 恢复 $ 符号
                    fmt = self._unescape_dollar_signs(fmt)
                    # 将 /* */ 改回 -- 格式
                    fmt = self._convert_block_comments_to_line_comments(fmt)
                    # TODO: 暂时禁用 V4 列对齐后处理，保证 SQL 完整性
                    # 问题：当前实现在处理子查询时会破坏 SQL 语法
                    # 后续计划：用 sqlglot AST 辅助识别 SELECT 子句范围后重新启用
                    # fmt = self._apply_v4_column_style(fmt)
                    # 添加分号
                    if not fmt.endswith(';'):
                        fmt += ';'
                    formatted.append(fmt)

                formatted_statements.extend(formatted)

            except Exception as e:
                # 单个语句解析失败，记录但继续处理其他语句
                error_msg = str(e)
                self._log(f"语句 {i+1} 解析失败", error_msg[:50] + '...')
                failed_statements.append((i + 1, stmt, error_msg))
                formatted_statements.append(stmt)

        # Step 3: 如果有任何语句失败，抛出错误
        if failed_statements:
            errors = []
            for idx, stmt, err in failed_statements:
                stmt_preview = stmt[:100] + '...' if len(stmt) > 100 else stmt

                # 检测常见错误并给出提示
                hint = ""
                if "Failed to parse any statement following CTE" in str(err):
                    hint = "    提示: CTE (WITH...AS) 后面需要跟 SELECT 语句，例如: WITH A AS (...) SELECT * FROM A"
                elif "Expecting )" in str(err):
                    hint = "    提示: 括号不匹配，请检查 SQL 中的括号是否成对"

                errors.append(f"  语句 {idx}: {err}\n    内容: {stmt_preview}")
                if hint:
                    errors.append(hint)

            error_msg = f"V5 格式化失败 ({len(failed_statements)} 个语句无法解析):\n" + "\n".join(errors)
            raise ValueError(error_msg)

        # Step 4: 合并结果
        return '\n\n'.join(formatted_statements)


def format_sql_v5(sql: str, **options) -> str:
    """v5 格式化入口函数"""
    formatter = SQLFormatterV5(
        indent_spaces=options.get('indent', 4)
    )
    return formatter.format(sql)

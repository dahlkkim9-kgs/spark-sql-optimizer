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
        - `a /* comment */ b` -> `a b  --comment` (注释后有内容时移到行末)
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

                # 检查注释后是否有内容
                after_comment = new_line[end:].strip()

                # 替换为 -- 格式
                replacement = f"--{comment_content}"

                if after_comment:
                    # 注释后有代码内容（如 ELSE、END 等），必须把注释移到行末
                    # 否则 -- 会把后面的代码也变成注释
                    if has_comma:
                        new_line = before_comment[:-1] + ' ' + after_comment + '  ' + replacement
                    else:
                        new_line = before_comment + ' ' + after_comment + '  ' + replacement
                elif has_comma:
                    new_line = before_comment[:-1] + ' ' + replacement + new_line[end:]
                else:
                    new_line = new_line[:start] + replacement + new_line[end:]

            result.append(new_line)

        return '\n'.join(result)

    # ============================================================
    # V4 风格后处理
    # ============================================================

    # 主 SQL 子句关键字（用于检测子句边界）
    _CLAUSE_KEYWORDS = [
        'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT',
        'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'FULL JOIN', 'CROSS JOIN',
        'JOIN', 'UNION ALL', 'UNION', 'INTERSECT', 'EXCEPT', 'WINDOW',
    ]

    def _is_clause_line(self, stripped: str) -> bool:
        """检测行是否以主子句关键字开头"""
        if not stripped:
            return False
        upper = stripped.upper()
        for kw in self._CLAUSE_KEYWORDS:
            if upper.startswith(kw) and (len(upper) == len(kw) or upper[len(kw)] in (' ', '(')):
                return True
        return False

    @staticmethod
    def _is_and_or(stripped: str) -> bool:
        """检测行是否以 AND 或 OR 开头"""
        upper = stripped.upper()
        return upper.startswith('AND ') or upper.startswith('OR ')

    def _apply_v4_full_style(self, sql: str) -> str:
        """Apply V4-style formatting to sqlglot output.

        转换规则：
        - SELECT/GROUP BY/ORDER BY: trailing comma → leading comma
        - FROM/JOIN/WHERE/HAVING: 关键字左对齐（0缩进）
        - ON: 2空格缩进，AND/OR 与 ON 右对齐
        - WHERE/HAVING: AND/OR 与关键字右对齐（2空格缩进）
        - CASE WHEN: 多行格式
        - HAVING: 与 WHERE 相同的 AND/OR 对齐
        """
        lines = sql.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            if not stripped:
                result.append('')
                i += 1
                continue

            upper = stripped.upper()

            # === WITH (CTE) ===
            if upper.startswith('WITH ') and '(' in stripped:
                result.append(stripped)
                i += 1
                continue

            # === SELECT (standalone keyword) ===
            if upper == 'SELECT':
                cols, i = self._collect_indented_cols(lines, i + 1, indent)
                if cols:
                    first_lines = self._format_column_with_case(cols[0])
                    # 判断是否为带标记的多行 CASE 或子查询
                    if first_lines and re.match(r'^[CWE]\d+\s', first_lines[0]):
                        result.append(f"{' ' * indent}SELECT")
                        self._append_case_inner_lines(result, first_lines, indent)
                    elif first_lines and first_lines[0].startswith('S '):
                        subquery_str = re.sub(r'^S\s+', '', first_lines[0])
                        self._append_subquery_col(result, subquery_str, ' ' * indent, indent)
                    else:
                        result.append(f"{' ' * indent}SELECT {first_lines[0]}")
                        if len(first_lines) > 1:
                            self._append_case_inner_lines(result, first_lines[1:], indent)
                    comma_prefix = ' ' * (indent + 5)
                    for c in cols[1:]:
                        col_lines = self._format_column_with_case(c)
                        # 先检测子查询标记（单元素但含换行）
                        if col_lines and len(col_lines) == 1 and col_lines[0].startswith('S '):
                            subquery_str = re.sub(r'^S\s+', '', col_lines[0])
                            self._append_subquery_col(result, subquery_str, comma_prefix, indent)
                        elif len(col_lines) == 1:
                            result.append(f"{comma_prefix}, {col_lines[0]}")
                        else:
                            # 判断是否为带标记的多行 CASE
                            if col_lines and re.match(r'^[CWE]\d+\s', col_lines[0]):
                                case_content = re.sub(r'^[CWE]\d+\s+', '', col_lines[0])
                                result.append(f"{comma_prefix}, {case_content}")
                                self._append_case_inner_lines(result, col_lines[1:], indent)
                            else:
                                result.append(f"{comma_prefix}, {col_lines[0]}")
                                self._append_case_inner_lines(result, col_lines[1:], indent)
                else:
                    result.append(f"{' ' * indent}SELECT")
                continue

            # === SELECT with first column on same line ===
            if upper.startswith('SELECT '):
                first_col = stripped[7:].rstrip(',')
                first_lines = self._format_column_with_case(first_col)
                if first_lines and re.match(r'^[CWE]\d+\s', first_lines[0]):
                    self._append_case_inner_lines(result, first_lines, indent)
                elif first_lines and first_lines[0].startswith('S '):
                    subquery_str = re.sub(r'^S\s+', '', first_lines[0])
                    self._append_subquery_col(result, subquery_str, ' ' * indent, indent)
                else:
                    result.append(f"{' ' * indent}SELECT {first_lines[0]}")
                    if len(first_lines) > 1:
                        self._append_case_inner_lines(result, first_lines[1:], indent)
                i += 1
                comma_prefix = ' ' * (indent + 5)
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s or (si <= indent and self._is_clause_line(s)):
                        break
                    if si <= indent and self._is_and_or(s):
                        break
                    col_content = s.rstrip(',')
                    col_lines = self._format_column_with_case(col_content)
                    if col_lines and len(col_lines) == 1 and col_lines[0].startswith('S '):
                        subquery_str = re.sub(r'^S\s+', '', col_lines[0])
                        self._append_subquery_col(result, subquery_str, comma_prefix, indent)
                    elif len(col_lines) == 1:
                        result.append(f"{comma_prefix}, {col_lines[0]}")
                    else:
                        if col_lines and re.match(r'^[CWE]\d+\s', col_lines[0]):
                            case_content = re.sub(r'^[CWE]\d+\s+', '', col_lines[0])
                            result.append(f"{comma_prefix}, {case_content}")
                            self._append_case_inner_lines(result, col_lines[1:], indent)
                    i += 1
                continue

            # === INSERT INTO (列定义 leading comma) ===
            # 排除 PARTITION(...) 语法，只匹配真正的列定义括号
            # INSERT INTO table (col1, col2) VALUES (...) ← 需要处理
            # INSERT INTO table PARTITION(dt='x') SELECT ... ← 不应匹配
            is_insert_with_cols = (
                upper.startswith('INSERT INTO')
                and '(' in stripped
                and not re.search(r'\bPARTITION\s*\(', stripped, re.IGNORECASE)
            )
            if is_insert_with_cols:
                result.append(stripped)
                i += 1
                inner_indent = indent + 2
                comma_prefix = ' ' * (inner_indent + 2)
                first = True
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s:
                        i += 1
                        continue
                    if s.startswith(')'):
                        result.append(' ' * inner_indent + s)
                        i += 1
                        break
                    col = s.rstrip(',')
                    if first:
                        result.append(' ' * inner_indent + col)
                        first = False
                    else:
                        result.append(f"{comma_prefix}, {col}")
                    i += 1
                # VALUES 后面的行保持原样
                while i < len(lines):
                    s = lines[i].strip()
                    if not s:
                        result.append('')
                    else:
                        result.append(' ' * indent + s)
                    i += 1
                continue

            # === CREATE TABLE (单行列定义拆分为多行 leading comma) ===
            if upper.startswith('CREATE TABLE') and '(' in stripped and not stripped.endswith('('):
                handled = False
                paren_start = stripped.index('(')
                # 检查 ( 是否为列定义（排除 PARTITION/STORED 等关键字后的括号）
                before_paren = stripped[:paren_start].rstrip()
                last_word = before_paren.split()[-1].upper() if before_paren.split() else ''
                skip_keywords = {'PARTITION', 'PARTITIONED', 'TBLPROPERTIES', 'BY'}

                if last_word not in skip_keywords:
                    # 查找匹配的 )
                    depth = 0
                    in_str = False
                    qc = None
                    paren_end = -1
                    for ci in range(paren_start, len(stripped)):
                        ch = stripped[ci]
                        if in_str:
                            if ch == qc:
                                in_str = False
                            continue
                        if ch in ("'", '"'):
                            in_str = True
                            qc = ch
                            continue
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                            if depth == 0:
                                paren_end = ci
                                break

                    if paren_end > paren_start:
                        table_prefix = stripped[:paren_start]
                        col_text = stripped[paren_start + 1:paren_end]
                        after_paren = stripped[paren_end + 1:].strip()

                        cols = self._split_set_columns(col_text)

                        if cols:
                            result.append(f"{' ' * indent}{table_prefix}")
                            result.append(f"{' ' * indent}(")
                            inner_indent = indent + 2
                            comma_prefix = ' ' * (inner_indent + 2)
                            for j, col in enumerate(cols):
                                col = col.strip()
                                if j == 0:
                                    result.append(f"{' ' * inner_indent}{col}")
                                else:
                                    result.append(f"{comma_prefix}, {col}")
                            if after_paren:
                                result.append(f"{' ' * indent}){after_paren}")
                            else:
                                result.append(f"{' ' * indent})")
                            handled = True

                if not handled:
                    result.append(f"{' ' * indent}{stripped}")
                i += 1
                continue

            # === CREATE TABLE (多行列定义 leading comma) ===
            if upper.startswith('CREATE TABLE') and '(' in stripped and stripped.endswith('('):
                result.append(stripped)
                i += 1
                inner_indent = indent + 2
                comma_prefix = ' ' * (inner_indent + 2)
                first = True
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s:
                        i += 1
                        continue
                    # 闭括号结束列定义
                    if s.startswith(')'):
                        result.append(' ' * inner_indent + s)
                        i += 1
                        break
                    col = s.rstrip(',')
                    if first:
                        result.append(' ' * inner_indent + col)
                        first = False
                    else:
                        result.append(f"{comma_prefix}, {col}")
                    i += 1
                # 继续处理闭括号后的内容（COMMENT、ROW FORMAT等）
                while i < len(lines):
                    s = lines[i].strip()
                    if not s:
                        result.append('')
                    else:
                        result.append(' ' * indent + s)
                    i += 1
                continue

            # === UPDATE SET (leading comma) ===
            if upper.startswith('UPDATE ') and ' SET ' in upper:
                # UPDATE t1 SET a = 1, b = 2 在同一行
                set_match = re.match(r'(UPDATE\s+\S+)\s+SET\s+(.*)', stripped, re.IGNORECASE)
                if set_match:
                    update_part = set_match.group(1)
                    set_rest = set_match.group(2)
                    # 安全分割 SET 列（排除括号内的逗号）
                    set_cols = self._split_set_columns(set_rest)
                    if set_cols:
                        result.append(f"{' ' * indent}{update_part}")
                        result.append(f"{' ' * indent}SET {set_cols[0]}")
                        set_prefix = ' ' * (indent + 4)
                        for sc in set_cols[1:]:
                            result.append(f"{set_prefix}, {sc}")
                    else:
                        result.append(stripped)
                else:
                    result.append(stripped)
                i += 1
                continue
            elif upper.startswith('UPDATE '):
                result.append(stripped)
                i += 1
                # SET 在下一行
                if i < len(lines):
                    next_stripped = lines[i].strip()
                    if next_stripped.upper().startswith('SET '):
                        set_rest = next_stripped[4:]
                        set_cols = self._split_set_columns(set_rest)
                        if set_cols:
                            set_prefix = ' ' * (indent + 4)
                            result.append(f"{' ' * indent}SET {set_cols[0]}")
                            for sc in set_cols[1:]:
                                result.append(f"{set_prefix}, {sc}")
                        else:
                            result.append(next_stripped)
                        i += 1
                continue

            # === FROM ===
            if upper.startswith('FROM '):
                result.append(' ' * indent + self._clean_table_alias(stripped))
                i += 1
                continue

            # === JOIN variants ===
            if self._is_join_line(stripped):
                result.append(' ' * indent + self._clean_table_alias(stripped))
                i += 1
                continue

            # === ON ===
            if upper.startswith('ON '):
                on_prefix = ' ' * indent
                and_prefix = ' ' * max(0, indent - 1)
                on_rest = stripped[3:]
                segments = self._split_and_or_in_line(on_rest)
                result.append(f"{on_prefix}ON {segments[0]}")
                for seg in segments[1:]:
                    result.append(f"{and_prefix}{seg}")
                i += 1
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s or (si <= indent and self._is_clause_line(s)):
                        break
                    if self._is_and_or(s):
                        result.append(f"{and_prefix}{s}")
                        i += 1
                    else:
                        break
                continue

            # === WHERE (standalone) ===
            if upper == 'WHERE':
                first_cond, i = self._merge_standalone_keyword(lines, i + 1, indent)
                if first_cond:
                    segments = self._split_and_or_in_line(first_cond)
                    result.append(f"{' ' * indent}WHERE {segments[0]}")
                    for seg in segments[1:]:
                        result.append(f"{' ' * (indent + 2)}{seg}")
                else:
                    result.append(f"{' ' * indent}WHERE")
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s or s == ')' or s.startswith(')'):
                        break
                    if si <= indent and (self._is_clause_line(s) or s.upper().startswith('SELECT')):
                        break
                    if self._is_and_or(s):
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                    else:
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                continue

            # === WHERE with condition ===
            if upper.startswith('WHERE '):
                where_cond = stripped[6:]  # Remove "WHERE "
                segments = self._split_and_or_in_line(where_cond)
                result.append(f"{' ' * indent}WHERE {segments[0]}")
                for seg in segments[1:]:
                    result.append(f"{' ' * (indent + 2)}{seg}")
                i += 1
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s or s == ')' or s.startswith(')'):
                        break
                    if si <= indent and (self._is_clause_line(s) or s.upper().startswith('SELECT')):
                        break
                    if self._is_and_or(s):
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                    else:
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                continue

            # === GROUP BY ===
            if upper.startswith('GROUP BY'):
                result, i = self._format_group_order(lines, i, indent, 'GROUP BY', result)
                continue

            # === HAVING (standalone) ===
            if upper == 'HAVING':
                first_cond, i = self._merge_standalone_keyword(lines, i + 1, indent)
                if first_cond:
                    segments = self._split_and_or_in_line(first_cond)
                    result.append(f"{' ' * indent}HAVING {segments[0]}")
                    for seg in segments[1:]:
                        result.append(f"{' ' * (indent + 2)}{seg}")
                else:
                    result.append(f"{' ' * indent}HAVING")
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s or s == ')' or s.startswith(')'):
                        break
                    if si <= indent and (self._is_clause_line(s) or s.upper().startswith('SELECT')):
                        break
                    if self._is_and_or(s):
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                    else:
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                continue

            # === HAVING with condition ===
            if upper.startswith('HAVING '):
                having_cond = stripped[7:]  # Remove "HAVING "
                segments = self._split_and_or_in_line(having_cond)
                result.append(f"{' ' * indent}HAVING {segments[0]}")
                for seg in segments[1:]:
                    result.append(f"{' ' * (indent + 2)}{seg}")
                i += 1
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s or s == ')' or s.startswith(')'):
                        break
                    if si <= indent and (self._is_clause_line(s) or s.upper().startswith('SELECT')):
                        break
                    if self._is_and_or(s):
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                    else:
                        result.append(f"{' ' * (indent + 2)}{s}")
                        i += 1
                continue

            # === ORDER BY ===
            if upper.startswith('ORDER BY'):
                result, i = self._format_group_order(lines, i, indent, 'ORDER BY', result)
                continue

            # === CASE WHEN (single-line, need to split) ===
            if upper.startswith('CASE') and 'WHEN' in stripped and '\n' not in stripped:
                case_lines = self._format_case_when_single(stripped, indent)
                result.extend(case_lines)
                i += 1
                continue

            # === CASE (already multi-line or complex) ===
            if upper.startswith('CASE'):
                result.append(stripped)
                i += 1
                continue

            # === LIMIT ===
            if upper.startswith('LIMIT '):
                result.append(' ' * indent + stripped)
                i += 1
                continue

            # === Standalone closing paren ===
            if stripped == ')':
                result.append(' ' * indent + stripped)
                i += 1
                continue

            # === Default: keep as-is ===
            result.append(' ' * indent + stripped)
            i += 1

        # 清理多余空行
        return self._cleanup_empty_lines('\n'.join(result))

    def _split_set_columns(self, set_rest: str) -> list:
        """安全分割 SET 子句的列赋值，排除括号和字符串内的逗号。"""
        cols = []
        current = []
        depth = 0
        in_str = False
        str_char = None
        for ch in set_rest:
            if in_str:
                current.append(ch)
                if ch == str_char:
                    in_str = False
            elif ch in ("'", '"'):
                in_str = True
                str_char = ch
                current.append(ch)
            elif ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
                depth -= 1
                current.append(ch)
            elif ch == ',' and depth == 0:
                cols.append(''.join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            cols.append(''.join(current).strip())
        return [c for c in cols if c]

    def _collect_indented_cols(self, lines, start_i, parent_indent):
        """收集缩进的列行，直到遇到同级或更低级的子句关键字或闭括号。

        多行 CASE 块被视为单个列单元，不会被拆分为多个列。
        子查询括号（下一行以 SELECT 开头）被视为单个列单元。
        普通函数括号（LPAD、COALESCE 等）内的多行参数也拼接到当前列。
        """
        cols = []
        i = start_i
        in_subquery = False  # 是否在子查询括号内
        in_func_parens = False  # 是否在函数调用括号内（非子查询）
        paren_depth = 0

        while i < len(lines):
            line = lines[i]
            s = line.strip()
            si = len(line) - len(s)
            if not s:
                break

            # 统计本行的括号（排除字符串内的括号）
            open_count = 0
            close_count = 0
            in_str = False
            str_char = None
            for ch in s:
                if in_str:
                    if ch == str_char:
                        in_str = False
                elif ch in ("'", '"'):
                    in_str = True
                    str_char = ch
                elif ch == '(':
                    open_count += 1
                elif ch == ')':
                    close_count += 1

            # 在闭括号处停止（顶层闭括号）
            if not in_subquery and not in_func_parens and paren_depth == 0 and (s == ')' or s.startswith(')')):
                break
            if si <= parent_indent and self._is_clause_line(s):
                break
            if si <= parent_indent and self._is_and_or(s):
                break

            # 如果这行是 CASE 块的开始，收集整个 CASE 块作为一个列
            if not in_subquery and not in_func_parens:
                if re.match(r'\bCASE\b', s, re.IGNORECASE) and not re.match(r'\bCASE\b.*\bEND\b', s, re.IGNORECASE):
                    case_str, i = self._collect_case_block(lines, i, si)
                    cols.append(case_str)
                    continue

            # 在子查询括号内
            if in_subquery:
                cols[-1] = cols[-1] + '\n' + line
                paren_depth += open_count - close_count
                if paren_depth <= 0:
                    paren_depth = 0
                    in_subquery = False
                    # 去掉闭括号行的尾部逗号
                    last_nl = cols[-1].rfind('\n')
                    if last_nl >= 0:
                        last_line = cols[-1][last_nl + 1:]
                        if last_line.strip().startswith(')'):
                            cols[-1] = cols[-1][:last_nl + 1] + last_line.rstrip(',')
                    i += 1
                    continue
                i += 1
                continue

            # 在函数括号内（非子查询）
            if in_func_parens:
                cols[-1] = cols[-1] + ' ' + s
                paren_depth += open_count - close_count
                if paren_depth <= 0:
                    paren_depth = 0
                    in_func_parens = False
                    # 去掉尾部逗号，清理括号内外多余空格
                    cols[-1] = cols[-1].rstrip(',')
                    cols[-1] = re.sub(r'\(\s+', '(', cols[-1])
                    cols[-1] = re.sub(r'\s+\)', ')', cols[-1])
                    i += 1
                    continue
                i += 1
                continue

            # 检查是否进入括号（子查询或函数调用）
            if open_count > close_count:
                if i + 1 < len(lines):
                    next_s = lines[i + 1].strip()
                    if re.match(r'^SELECT\b', next_s, re.IGNORECASE):
                        # 子查询
                        in_subquery = True
                        paren_depth = open_count - close_count
                        cols.append(line.rstrip())
                        i += 1
                        continue
                    else:
                        # 函数调用（LPAD, COALESCE 等），下一行不是 SELECT
                        in_func_parens = True
                        paren_depth = open_count - close_count
                        cols.append(s)  # 只保留内容，不带原始缩进
                        i += 1
                        continue

            # 普通行，正常收集
            cols.append(s.rstrip(','))
            i += 1
        return cols, i

    def _collect_case_block(self, lines, start_i, case_indent):
        """收集完整的 CASE 块作为一个字符串，处理嵌套 CASE。

        Returns:
            (joined_string, next_line_index)
        """
        collected = []
        i = start_i
        case_depth = 0

        while i < len(lines):
            s = lines[i].strip()
            si = len(lines[i]) - len(lines[i].lstrip())

            upper_s = s.upper()

            # CASE 内部关键字（WHEN/THEN/ELSE/END）始终属于 CASE 块，不受缩进限制
            is_case_inner = bool(re.match(r'\b(CASE|WHEN|THEN|ELSE|END)\b', upper_s))

            # 非 CASE 内部行，如果回到了 CASE 的缩进级别且 depth 为 0，停止
            if not is_case_inner and case_depth == 0 and i > start_i:
                if si <= case_indent or si < case_indent:
                    break

            # 跟踪 CASE/END 深度
            if re.match(r'\bCASE\b', upper_s):
                case_depth += 1
                # 同一行有 END（单行 CASE），深度不增加
                if re.search(r'\bEND\b', upper_s):
                    case_depth -= 1

            collected.append(s.rstrip(','))

            if re.match(r'\bEND\b', upper_s) and not re.match(r'\bCASE\b.*\bEND\b', upper_s, re.IGNORECASE):
                case_depth -= 1
                if case_depth == 0:
                    i += 1
                    break

            i += 1

        return '\n'.join(collected), i

    def _merge_standalone_keyword(self, lines, start_i, parent_indent):
        """合并独立关键字与下一行的内容（如 standalone WHERE + condition）"""
        if start_i >= len(lines):
            return '', start_i
        s = lines[start_i].strip()
        si = len(lines[start_i]) - len(lines[start_i].lstrip())
        if s and s != ')' and not s.startswith(')') and not (si <= parent_indent and self._is_clause_line(s)) and not self._is_and_or(s):
            # 癩以CTE name AS (独立关键字（如 "), high_paid_depts") - 不不会被误合并
            return s, start_i + 1
        return '', start_i

    def _format_group_order(self, lines, start_i, indent, keyword, result):
        """格式化 GROUP BY / ORDER BY 子句（leading comma）"""
        stripped = lines[start_i].strip()
        rest = stripped[len(keyword):].strip()
        i = start_i

        if rest:
            result.append(f"{' ' * indent}{keyword} {rest.rstrip(',')}")
            i += 1
        else:
            i += 1
            first_cond, i = self._merge_standalone_keyword(lines, i, indent)
            if first_cond:
                result.append(f"{' ' * indent}{keyword} {first_cond.rstrip(',')}")
            else:
                result.append(f"{' ' * indent}{keyword}")

        comma_prefix = ' ' * (indent + 7)
        while i < len(lines):
            s = lines[i].strip()
            si = len(lines[i]) - len(lines[i].lstrip())
            if not s:
                break
            # 在闭括号处停止
            if s == ')' or s.startswith(')'):
                break
            if si <= indent and self._is_clause_line(s):
                break
            if self._is_and_or(s):
                break
            c = s.rstrip(',')
            if c:
                result.append(f"{comma_prefix}, {c}")
            i += 1

        return result, i

    @staticmethod
    def _split_and_or_in_line(text):
        """按顶层 AND/OR 关键字拆分条件行为多行。

        每个段包含完整内容（AND/OR 与其后的条件在同一行）。
        忽略字符串和括号内的 AND/OR。

        Returns:
            list of segments，如 ['cond1', 'AND cond2', 'OR cond3']
        """
        segments = []
        depth = 0
        in_string = False
        quote_char = None
        current_start = 0

        for i, c in enumerate(text):
            if in_string:
                if c == quote_char:
                    in_string = False
                continue
            if c in ("'", '"'):
                in_string = True
                quote_char = c
                continue
            if c == '(':
                depth += 1
                continue
            if c == ')':
                depth -= 1
                continue

            if depth == 0:
                remaining = text[i:]
                m = re.match(r'\b(AND|OR)\b\s+', remaining, re.IGNORECASE)
                if m:
                    cond = text[current_start:i].strip()
                    if cond:
                        segments.append(cond)
                    # 从 AND/OR 位置开始新段（包含后续条件）
                    current_start = i

        # 添加剩余部分
        remaining = text[current_start:].strip()
        if remaining:
            segments.append(remaining)

        return segments

    def _output_condition_with_and_or(self, condition, indent, and_or_indent):
        """输出条件行，自动拆分 AND/OR 为多行。

        Args:
            condition: 条件字符串（可能包含 AND/OR）
            indent: 首行缩进
            and_or_indent: AND/OR 行的缩进

        Returns:
            list of output lines
        """
        segments = self._split_and_or_in_line(condition)
        lines = []
        for j, seg in enumerate(segments):
            if j == 0:
                lines.append(f"{' ' * indent}{seg}")
            else:
                lines.append(f"{' ' * and_or_indent}{seg}")
        return lines

    @staticmethod
    def _find_case_end(text, start=0):
        """找到 CASE 关键字对应的 END 位置（处理嵌套 CASE WHEN）。

        Returns:
            END 关键字结束位置的索引，未找到返回 -1
        """
        case_depth = 0
        in_string = False
        quote_char = None
        i = start

        while i < len(text):
            c = text[i]

            if in_string:
                if c == quote_char:
                    in_string = False
                i += 1
                continue

            if c in ("'", '"'):
                in_string = True
                quote_char = c
                i += 1
                continue

            # 检查 CASE 关键字
            if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE':
                before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                after_ok = (i + 4 >= len(text) or not text[i + 4].isalnum() and text[i + 4] != '_')
                if before_ok and after_ok:
                    case_depth += 1
                    i += 4
                    continue

            # 检查 END 关键字
            if i + 3 <= len(text) and text[i:i + 3].upper() == 'END':
                before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                after_ok = (i + 3 >= len(text) or not text[i + 3].isalnum() and text[i + 3] != '_')
                if before_ok and after_ok:
                    case_depth -= 1
                    if case_depth == 0:
                        return i + 3
                    i += 3
                    continue

            i += 1

        return -1

    @staticmethod
    def _find_top_level_else(text):
        """在文本中找到顶层 ELSE 关键字的位置（跳过嵌套 CASE...END 内的 ELSE）。

        Args:
            text: 要搜索的文本（通常是 THEN 之后的剩余部分）

        Returns:
            ELSE 关键字的起始位置索引，未找到返回 -1
        """
        case_depth = 0
        paren_depth = 0
        in_string = False
        quote_char = None
        i = 0

        while i < len(text):
            c = text[i]

            if in_string:
                if c == quote_char:
                    in_string = False
                i += 1
                continue

            if c in ("'", '"'):
                in_string = True
                quote_char = c
                i += 1
                continue

            if c == '(':
                paren_depth += 1
                i += 1
                continue

            if c == ')':
                paren_depth -= 1
                i += 1
                continue

            if paren_depth == 0:
                # 检查 CASE
                if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE':
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_ok = (i + 4 >= len(text) or not text[i + 4].isalnum() and text[i + 4] != '_')
                    if before_ok and after_ok:
                        case_depth += 1
                        i += 4
                        continue

                # 检查 END
                if i + 3 <= len(text) and text[i:i + 3].upper() == 'END':
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_ok = (i + 3 >= len(text) or not text[i + 3].isalnum() and text[i + 3] != '_')
                    if before_ok and after_ok:
                        case_depth -= 1
                        i += 3
                        continue

                # 只在 case_depth == 0 时匹配 ELSE
                if case_depth == 0 and i + 4 <= len(text) and text[i:i + 4].upper() == 'ELSE':
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_ok = (i + 4 >= len(text) or not text[i + 4].isalnum() and text[i + 4] != '_')
                    if before_ok and after_ok:
                        return i

            i += 1

        return -1

    @staticmethod
    def _split_top_level_when(text):
        """按顶层 WHEN 关键字拆分文本（忽略嵌套 CASE 和括号内的 WHEN）。

        Returns:
            list of segments，第一个是 WHEN 之前的内容，后续是 WHEN 及其后内容
        """
        parts = []
        paren_depth = 0
        case_depth = 0
        in_string = False
        quote_char = None
        current_start = 0
        i = 0

        while i < len(text):
            c = text[i]

            if in_string:
                if c == quote_char:
                    in_string = False
                i += 1
                continue

            if c in ("'", '"'):
                in_string = True
                quote_char = c
                i += 1
                continue

            if c == '(':
                paren_depth += 1
                i += 1
                continue

            if c == ')':
                paren_depth -= 1
                i += 1
                continue

            if paren_depth == 0:
                # 检查 CASE
                if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE':
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_ok = (i + 4 >= len(text) or not text[i + 4].isalnum() and text[i + 4] != '_')
                    if before_ok and after_ok:
                        case_depth += 1
                        i += 4
                        continue

                # 检查 END
                if i + 3 <= len(text) and text[i:i + 3].upper() == 'END':
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_ok = (i + 3 >= len(text) or not text[i + 3].isalnum() and text[i + 3] != '_')
                    if before_ok and after_ok:
                        case_depth -= 1
                        i += 3
                        continue

                # 只在顶层 CASE 中拆分 WHEN（case_depth == 0 表示外层 CASE 已剥离）
                if case_depth == 0 and i + 4 <= len(text) and text[i:i + 4].upper() == 'WHEN':
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_ok = (i + 4 >= len(text) or not text[i + 4].isalnum() and text[i + 4] != '_')
                    if before_ok and after_ok:
                        parts.append(text[current_start:i])
                        current_start = i
                        i += 4
                        continue

            i += 1

        parts.append(text[current_start:])
        return parts

    def _format_case_when_single(self, case_str, base_indent=0):
        """将单行 CASE WHEN 拆分为多行格式（不添加基础缩进，由调用者处理）。

        正确处理嵌套 CASE WHEN 和括号内的 WHEN。
        正确处理 END 后跟别名的情况（如 CASE ... END AS alias）。
        """
        # 使用括号感知的方法找到匹配的 END 位置
        case_match = re.search(r'\bCASE\b', case_str, re.IGNORECASE)
        trailing = ''
        if case_match:
            case_end = self._find_case_end(case_str, case_match.start())
            if case_end != -1:
                # 提取 CASE...END 部分，END 后面的内容作为 trailing
                case_body = case_str[case_match.start():case_end]
                trailing = case_str[case_end:].strip()
            else:
                case_body = case_str
        else:
            case_body = case_str

        # 从 case_body 中移除 CASE 前缀和 END 后缀
        inner = case_body
        if inner.upper().startswith('CASE '):
            inner = inner[5:]
        elif inner.upper().startswith('CASE'):
            inner = inner[4:]
        if inner.upper().rstrip().endswith(' END'):
            inner = inner.rstrip()[:-4]
        elif inner.rstrip().upper().endswith('END'):
            inner = inner.rstrip()[:-3]
        inner = inner.strip()

        result = ['CASE']

        parts = self._split_top_level_when(inner)

        for j, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            then_match = re.search(r'\bTHEN\b', part, re.IGNORECASE)
            if then_match:
                condition = part[:then_match.start()].strip()
                # 去除 condition 开头的 WHEN 关键字（_split_top_level_when 保留的）
                condition = re.sub(r'^WHEN\s+', '', condition, flags=re.IGNORECASE)
                rest = part[then_match.end():].strip()
                # 使用 CASE 深度感知的 ELSE 检测，避免匹配嵌套 CASE 内的 ELSE
                else_pos = self._find_top_level_else(rest)
                if else_pos != -1:
                    then_val = rest[:else_pos].strip()
                    else_val = rest[else_pos + 4:].strip()
                    result.append(f"    WHEN {condition}")
                    result.append(f"    THEN {then_val}")
                    result.append(f"    ELSE {else_val}")
                else:
                    result.append(f"    WHEN {condition}")
                    result.append(f"    THEN {rest}")
            else:
                if part.upper().startswith('ELSE '):
                    result.append(f"    ELSE {part[5:].strip()}")
                else:
                    result.append(f"    {part}")

        end_line = 'END'
        if trailing:
            end_line = f'END {trailing}'
        result.append(end_line)
        return result

    @staticmethod
    def _is_join_line(stripped):
        """检测是否是 JOIN 行"""
        return bool(re.match(
            r'^(LEFT|RIGHT|INNER|FULL|CROSS)?\s*JOIN\s+',
            stripped, re.IGNORECASE
        ))

    @staticmethod
    def _clean_table_alias(line):
        """移除表别名中的 AS 关键字（V4 风格），只合并多余空格"""
        return re.sub(r'\s+AS\b\s+', ' ', line, flags=re.IGNORECASE)

    @staticmethod
    def _cleanup_empty_lines(text):
        """清理多余空行，最多保留一个连续空行"""
        lines = text.split('\n')
        cleaned = []
        prev_empty = False
        for line in lines:
            if line.strip() == '':
                if not prev_empty:
                    cleaned.append(line)
                prev_empty = True
            else:
                cleaned.append(line)
                prev_empty = False
        return '\n'.join(cleaned)

    @staticmethod
    def _split_when_then(content):
        """将同一行的 WHEN...THEN...WHEN...THEN 拆分为独立段。

        正确处理字符串、括号、嵌套 CASE/END 内的 THEN（不拆分）。

        Example:
            'WHEN a=1 THEN x WHEN b=2 THEN y'
            -> ['WHEN a=1', 'THEN x', 'WHEN b=2', 'THEN y']
        """
        result = []
        depth = 0
        case_depth = 0
        in_str = False
        qc = None
        i = 0
        seg_start = 0

        def _kw(pos, kw):
            e = pos + len(kw)
            if e > len(content):
                return False
            if content[pos:e].upper() != kw:
                return False
            if pos > 0 and (content[pos - 1].isalnum() or content[pos - 1] == '_'):
                return False
            if e < len(content) and (content[e].isalnum() or content[e] == '_'):
                return False
            return True

        while i < len(content):
            c = content[i]
            if in_str:
                if c == qc:
                    in_str = False
                i += 1
                continue
            if c in ("'", '"'):
                in_str = True
                qc = c
                i += 1
                continue
            if c == '(':
                depth += 1
                i += 1
                continue
            if c == ')':
                depth -= 1
                i += 1
                continue

            if depth == 0 and _kw(i, 'CASE'):
                case_depth += 1
                i += 4
                continue
            if depth == 0 and case_depth > 0 and _kw(i, 'END'):
                case_depth -= 1
                i += 3
                continue

            if depth == 0 and case_depth == 0:
                if _kw(i, 'THEN'):
                    seg = content[seg_start:i].strip()
                    if seg:
                        result.append(seg)
                    seg_start = i  # THEN 作为下一段的开头
                    i += 4
                    continue
                if i > seg_start and _kw(i, 'WHEN'):
                    seg = content[seg_start:i].strip()
                    if seg:
                        result.append(seg)
                    seg_start = i
                    i += 4
                    continue

            i += 1

        seg = content[seg_start:].strip()
        if seg:
            result.append(seg)
        return result

    @staticmethod
    def _merge_case_lines(lines):
        """将 sqlglot pretty 拆散的 WHEN 条件行重新合并为一行。

        sqlglot pretty=True 会把括号内容拆成多行：
            WHEN (
              a.type = 'B' OR a.type = 'C'
            )
            AND a.status = '0'

        合并后：
            WHEN (a.type = 'B' OR a.type = 'C') AND a.status = '0'

        也处理 THEN (CASE ... END) 嵌套模式：
            THEN (
            CASE
                WHEN ...
            END
            )
        合并为单行 THEN (CASE WHEN ... END)，供后续展开。
        """
        merged = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                continue

            upper = stripped.upper()

            # CASE / END 始终独立
            if re.match(r'\bCASE\b', upper) or re.match(r'\bEND\b', upper):
                merged.append(stripped)
                i += 1
                continue

            # THEN / ELSE 始终独立（除非以 ( 结尾，表示后续有嵌套块）
            if re.match(r'\b(THEN|ELSE)\b', upper) and not stripped.endswith('('):
                merged.append(stripped)
                i += 1
                continue

            # 其他行（WHEN 条件、AND/OR 续行、括号内容）：合并到下一个边界
            accumulated = stripped
            open_parens = accumulated.count('(') - accumulated.count(')')
            i += 1
            while i < len(lines):
                next_s = lines[i].strip()
                if not next_s:
                    i += 1
                    continue
                next_upper = next_s.upper()

                # 如果有未闭合的括号，继续合并直到括号全部闭合
                if open_parens > 0:
                    open_parens += next_s.count('(') - next_s.count(')')
                    accumulated += ' ' + next_s
                    i += 1
                    if open_parens <= 0:
                        break
                    continue

                # 括号已全部闭合，检查关键字边界
                is_boundary = re.match(r'\b(CASE|END|WHEN|THEN|ELSE)\b', next_upper)
                if is_boundary:
                    break
                accumulated += ' ' + next_s
                i += 1

            # 清理括号内外多余空格
            accumulated = re.sub(r'\(\s+', '(', accumulated)
            accumulated = re.sub(r'\s+\)', ')', accumulated)
            merged.append(accumulated)

        return merged

    def _format_multiline_case_block(self, block: str) -> list:
        """格式化多行 CASE 块，用缩进标记表示嵌套层级。

        输入来自 _collect_case_block，是已经由 sqlglot 拆分为多行的 CASE 块。

        返回的行带有前缀标记：
        - 'C' + depth: CASE 行（如 'C1' 表示 depth=1 的 CASE）
        - 'E' + depth: END 行
        - 'W' + depth: WHEN/THEN/ELSE 等内部行
        由 _append_case_inner_lines 根据标记和 base_indent 计算实际缩进。

        Returns:
            list of marked lines
        """
        lines = block.split('\n')
        if not lines:
            return [block]

        # 合并 sqlglot pretty 拆散的括号行
        merged = self._merge_case_lines(lines)

        result = []
        case_depth = 0

        for line in merged:
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()

            # 跟踪嵌套 CASE 深度
            if re.match(r'\bCASE\b', upper) and not re.match(r'\bCASE\b.*\bEND\b', upper):
                case_depth += 1
                result.append(f"C{case_depth} {stripped}")
                continue

            if re.match(r'\bEND\b', upper):
                result.append(f"E{case_depth} {stripped}")
                case_depth = max(0, case_depth - 1)
                continue

            # WHEN/THEN/ELSE 等内容行
            # 如果同一行包含 WHEN...THEN，拆分为独立段
            if re.match(r'\bWHEN\b', upper) and re.search(r'\bTHEN\b', upper):
                segments = self._split_when_then(stripped)
                for seg in segments:
                    result.append(f"W{case_depth} {seg}")
            elif re.search(r'\bCASE\b.*\bEND\b', upper, re.IGNORECASE):
                # 同一行包含完整嵌套 CASE...END（如 THEN (CASE WHEN ... END)）
                self._expand_embedded_case(result, stripped, case_depth)
            else:
                result.append(f"W{case_depth} {stripped}")

        return result

    def _expand_embedded_case(self, result, line, depth):
        """递归展开包含嵌套 CASE...END 的行。

        处理如 THEN (CASE WHEN ... THEN (CASE ... END) ... END) 的多层嵌套。
        展开结果直接追加到 result 列表中，带有正确的深度标记。

        Args:
            result: 输出行列表
            line: 包含 CASE...END 的行文本
            depth: 当前 CASE 深度
        """
        stripped = line.strip() if isinstance(line, str) else str(line)

        upper = stripped.upper()
        case_match = re.search(r'\bCASE\b', stripped, re.IGNORECASE)
        end_match = re.search(r'\bEND\b(?=\)*\s*$)', stripped, re.IGNORECASE)

        if not (case_match and end_match):
            result.append(f"W{depth} {stripped}")
            return

        before = stripped[:case_match.start()].strip()
        inner_case = stripped[case_match.start():end_match.end()]
        after = stripped[end_match.end():].strip()

        if before:
            result.append(f"W{depth} {before}")

        # 展开内层 CASE
        inner_lines = self._format_case_when_single(inner_case)
        inner_depth = depth + 1

        for il in inner_lines:
            il_s = il.strip()
            il_upper = il_s.upper()

            if re.match(r'\bCASE\b', il_upper):
                result.append(f"C{inner_depth} {il_s}")
            elif re.match(r'\bEND\b', il_upper):
                result.append(f"E{inner_depth} {il_s}")
            elif re.search(r'\bCASE\b.*\bEND\b', il_upper):
                # 递归展开更深层嵌套（如3层+）
                self._expand_embedded_case(result, il_s, inner_depth)
            else:
                result.append(f"W{inner_depth} {il_s}")

        # after 可能是 ) 或其他内容
        if after:
            if after == ')':
                result.append(f"P{inner_depth} )")
            else:
                result.append(f"W{depth} {after}")

    def _format_column_with_case(self, column_str):
        """格式化列字符串，如果包含 CASE WHEN 则拆分为多行。

        支持单行 CASE（从 sqlglot 紧凑输出）和多行 CASE（从 _collect_case_block）。
        多行子查询列保持原样（带 'S' 标记），由调用者处理缩进。

        Returns:
            list of formatted lines（不含前导缩进，由调用者处理）
        """
        case_match = re.search(r'\bCASE\b', column_str, re.IGNORECASE)
        if case_match:
            # 多行 CASE 块（来自 _collect_case_block）
            if '\n' in column_str:
                return self._format_multiline_case_block(column_str)
            # 继续走下面的单行 CASE 处理
        elif '\n' in column_str:
            # 多行子查询列，用 'S' 标记
            return ['S ' + column_str]

        if not case_match:
            return [column_str]

        # 单行 CASE：使用括号感知的方法找到匹配的 END
        case_end = self._find_case_end(column_str, case_match.start())
        if case_end == -1:
            return [column_str]

        before = column_str[:case_match.start()].strip()
        case_str = column_str[case_match.start():case_end]
        after = column_str[case_end:].strip()

        case_lines = self._format_case_when_single(case_str)

        result = []
        if before:
            result.append(before)

        for cl in case_lines:
            result.append(cl)

        if after:
            result[-1] = f"{result[-1]} {after}"

        return result

    def _append_subquery_col(self, result, subquery_str, comma_prefix, base_indent):
        """将多行子查询列添加到结果中，保持 sqlglot 的缩进结构。

        Args:
            result: 输出行列表
            subquery_str: 多行子查询字符串（带原始缩进）
            comma_prefix: leading comma 的前缀（如 '     '）
            base_indent: 子查询的基础缩进（从 sqlglot 输出中检测）
        """
        lines = subquery_str.split('\n')
        if not lines:
            return

        # 找到最小缩进（排除空行）
        min_indent = float('inf')
        for line in lines:
            stripped = line.lstrip()
            if stripped:
                min_indent = min(min_indent, len(line) - len(stripped))
        if min_indent == float('inf'):
            min_indent = 0

        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped:
                continue
            line_indent = len(line) - len(stripped)
            # 重新计算缩进：以 comma_prefix 为基准
            new_indent = line_indent - min_indent + len(comma_prefix)
            if idx == 0:
                result.append(f"{comma_prefix}, {stripped}")
            else:
                result.append(f"{' ' * new_indent}{stripped}")

    @staticmethod
    def _and_or_indent(base_indent, content):
        """计算 AND/OR 续行的缩进，右对齐上面的关键字（WHEN/THEN/ELSE=4字符）。

        WHEN(4) + AND(3) → +1
        WHEN(4) + OR(2)  → +2
        """
        content_upper = content.lstrip().upper()
        if re.match(r'\bOR\b', content_upper):
            return base_indent + 2
        return base_indent + 1  # AND

    def _append_case_inner_lines(self, result, inner_lines, indent):
        """将 CASE WHEN 内部行（WHEN/ELSE/END）添加到结果中，正确处理缩进。

        支持两种输入格式：
        1. 带标记的多行 CASE 块（来自 _format_multiline_case_block）：
           'C{depth} ...' / 'W{depth} ...' / 'E{depth} ...' / 'P{depth} ...'
        2. 纯文本行（来自 _format_case_when_single）：
           无标记，按 WHEN/ELSE/END 关键字判断

        缩进规则（基于列的 leading comma 位置）：
        - depth=1 CASE: indent + 7, WHEN/THEN/ELSE: indent + 11, END: indent + 7
        - depth>1 嵌套: CASE/END 相对外层 WHEN 缩进+6, WHEN/THEN 相对 CASE 缩进+4
        - AND/OR 续行: 右对齐上面关键字 (WHEN+1 / WHEN+2)
        - P 标记: 闭括号，与同深度 CASE/END 对齐减1格
        """
        base_case = indent + 7   # depth=1 CASE/END 基础缩进
        base_inner = indent + 11  # depth=1 WHEN/THEN/ELSE 基础缩进

        for line in inner_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 检测标记格式: C{depth} / W{depth} / E{depth} / P{depth}
            marker_match = re.match(r'^([CWEP])(\d+)\s+(.+)$', stripped)
            if marker_match:
                marker_type = marker_match.group(1)
                depth = int(marker_match.group(2))
                content = marker_match.group(3)

                if depth == 1:
                    # 外层 CASE 块
                    if marker_type == 'C' or marker_type == 'E':
                        result.append(f"{' ' * base_case}{content}")
                    else:
                        # W (WHEN/THEN/ELSE/AND/OR)
                        # AND/OR 续行右对齐关键字
                        content_upper = content.upper().lstrip()
                        if re.match(r'\b(AND|OR)\b', content_upper):
                            result.append(f"{' ' * self._and_or_indent(base_inner, content)}{content}")
                        else:
                            output_line = f"{' ' * base_inner}{content}"
                            if len(output_line) > 250:
                                segments = self._split_and_or_in_line(content)
                                if len(segments) > 1:
                                    result.append(f"{' ' * base_inner}{segments[0]}")
                                    for seg in segments[1:]:
                                        result.append(f"{' ' * self._and_or_indent(base_inner, seg)}{seg}")
                                    continue
                            result.append(output_line)
                else:
                    # 嵌套 CASE 块（depth > 1）
                    nested_case = base_inner + (depth - 1) * 6   # CASE/END 缩进
                    nested_when = base_inner + (depth - 1) * 6 + 4  # WHEN/THEN 缩进

                    if marker_type == 'C' or marker_type == 'E':
                        result.append(f"{' ' * nested_case}{content}")
                    elif marker_type == 'P':
                        # 闭括号：与同深度 CASE/END 对齐减1格
                        result.append(f"{' ' * (nested_case - 1)}{content}")
                    else:
                        # W (WHEN/THEN/ELSE/AND/OR)
                        content_upper = content.upper().lstrip()
                        if re.match(r'\b(AND|OR)\b', content_upper):
                            result.append(f"{' ' * self._and_or_indent(nested_when, content)}{content}")
                        else:
                            output_line = f"{' ' * nested_when}{content}"
                            if len(output_line) > 250:
                                segments = self._split_and_or_in_line(content)
                                if len(segments) > 1:
                                    result.append(f"{' ' * nested_when}{segments[0]}")
                                    for seg in segments[1:]:
                                        result.append(f"{' ' * self._and_or_indent(nested_when, seg)}{seg}")
                                    continue
                            result.append(output_line)
            else:
                # 纯文本行（单行 CASE 拆分结果）
                if stripped.startswith('END'):
                    result.append(f"{' ' * base_case}{stripped}")
                else:
                    stripped_upper = stripped.upper().lstrip()
                    if re.match(r'\b(AND|OR)\b', stripped_upper):
                        result.append(f"{' ' * self._and_or_indent(base_inner, stripped)}{stripped}")
                    else:
                        output_line = f"{' ' * base_inner}{stripped}"
                        if len(output_line) > 250:
                            segments = self._split_and_or_in_line(stripped)
                            if len(segments) > 1:
                                result.append(f"{' ' * base_inner}{segments[0]}")
                                for seg in segments[1:]:
                                    result.append(f"{' ' * self._and_or_indent(base_inner, seg)}{seg}")
                                continue
                        result.append(output_line)

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

    def _fix_subquery_indent(self, text):
        """修复子查询内的缩进不一致和括号不对齐问题。

        规则：
        - 子查询内容起始缩进 = ( 列位置 + 1
        - 闭括号 ) 与开括号 ( 对齐
        - 递归处理嵌套子查询
        - 合并非子查询的独立括号行（如 AND ( → AND (...)）
        """
        lines = text.split('\n')
        result, _ = self._fix_subquery_lines(lines, 0)
        return '\n'.join(result)

    def _fix_subquery_lines(self, lines, start):
        """递归处理子查询缩进。

        Returns:
            (processed_lines, next_index)
        """
        result = []
        i = start
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检测子查询起始：行尾 ( 且下一行是 SELECT
            is_subquery_start = False
            open_paren_col = 0

            if stripped.endswith('(') and i + 1 < len(lines):
                next_s = lines[i + 1].strip()
                # 跳过 CTE 模式：WITH name AS ( 和 ), name AS (
                is_cte = (
                    re.match(r'^WITH\b', stripped, re.IGNORECASE)
                    or re.match(r'^\)\s*,', stripped)
                )
                if re.match(r'^SELECT\b', next_s, re.IGNORECASE) and not is_cte:
                    is_subquery_start = True
                    # 计算 ( 在行中的实际列位置
                    paren_pos = line.index('(')
                    open_paren_col = paren_pos

            if not is_subquery_start:
                # 检查非子查询的独立括号行（如 AND (, WHERE (），合并到下一行
                if stripped.endswith('(') and i + 1 < len(lines):
                    next_s = lines[i + 1].strip()
                    # 跳过 CASE 块 — 已由 _apply_v4_full_style 格式化，不应合并
                    if re.match(r'^CASE\b', next_s, re.IGNORECASE):
                        result.append(line)
                        i += 1
                        continue
                    # 跳过 CREATE TABLE 列定义 — 已由 _apply_v4_full_style 格式化
                    if re.match(r'^(CREATE|DROP)\b', stripped, re.IGNORECASE):
                        result.append(line)
                        i += 1
                        continue
                    if not re.match(r'^SELECT\b', next_s, re.IGNORECASE):
                        # 不是子查询，合并括号行
                        merged_line = line.rstrip() + next_s.lstrip()
                        # 检查合并后是否还有未闭合的括号
                        open_p = merged_line.count('(') - merged_line.count(')')
                        k = i + 2
                        while open_p > 0 and k < len(lines):
                            ns = lines[k].strip()
                            if not ns:
                                k += 1
                                continue
                            open_p += ns.count('(') - ns.count(')')
                            merged_line += ' ' + ns
                            k += 1
                        # 清理括号内外多余空格
                        merged_line = re.sub(r'\(\s+', '(', merged_line)
                        merged_line = re.sub(r'\s+\)', ')', merged_line)
                        result.append(merged_line)
                        i = k
                        continue

                result.append(line)
                i += 1
                continue

            # 收集子查询全部内容（含开闭括号）
            sub_lines = [line]
            paren_depth = 0
            in_str = False
            qc = None
            for ch in stripped:
                if in_str:
                    if ch == qc:
                        in_str = False
                elif ch in ("'", '"'):
                    in_str = True
                    qc = ch
                elif ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1

            j = i + 1
            while j < len(lines) and paren_depth > 0:
                s = lines[j].strip()
                in_str = False
                qc = None
                for ch in s:
                    if in_str:
                        if ch == qc:
                            in_str = False
                    elif ch in ("'", '"'):
                        in_str = True
                        qc = ch
                    elif ch == '(':
                        paren_depth += 1
                    elif ch == ')':
                        paren_depth -= 1
                sub_lines.append(lines[j])
                j += 1

            # 找 SELECT 行的缩进作为基准
            select_indent = None
            for sl in sub_lines[1:]:
                ss = sl.strip()
                if re.match(r'^SELECT\b', ss, re.IGNORECASE):
                    select_indent = len(sl) - len(ss)
                    break
            if select_indent is None:
                select_indent = open_paren_col + 1

            # 目标缩进：( 列位置 + 1
            target = open_paren_col + 1

            # 重新缩进子查询内容（不含首行和末行）
            result.append(sub_lines[0])
            inner_reindented = []
            for sl in sub_lines[1:-1]:
                ss = sl.strip()
                if not ss:
                    continue
                sl_i = len(sl) - len(ss)
                new_i = sl_i - select_indent + target
                if new_i < target:
                    new_i = target
                inner_reindented.append(f"{' ' * new_i}{ss}")

            # 递归处理嵌套子查询
            inner_fixed, _ = self._fix_subquery_lines(inner_reindented, 0)
            result.extend(inner_fixed)

            # 闭括号对齐 (
            last_s = sub_lines[-1].strip()
            if last_s.startswith(')'):
                result.append(f"{' ' * open_paren_col}{last_s}")
            else:
                result.append(sub_lines[-1])

            i = j
        return result, i

    # ============================================================
    # 长行标量子查询拆分
    # ============================================================

    def _split_long_scalar_subqueries(self, text: str) -> str:
        """拆分超长标量子查询为多行格式。

        处理两种模式：
        1. EXISTS(SELECT...)/NOT EXISTS(SELECT...) — 在 CASE WHEN 或 WHERE 中
        2. 函数内标量子查询 — 如 AVG(COALESCE((SELECT...), 0))

        只处理超过 120 字符的行。
        """
        lines = text.split('\n')
        result = []
        for line in lines:
            if len(line) > 120 and self._contains_scalar_subquery(line.strip()):
                expanded = self._expand_scalar_subquery_in_line(line)
                result.extend(expanded)
            else:
                result.append(line)
        return '\n'.join(result)

    @staticmethod
    def _contains_scalar_subquery(text: str) -> bool:
        """检测文本是否包含标量子查询模式。"""
        # 模式1: EXISTS(SELECT...) 或 NOT EXISTS(SELECT...)
        if re.search(r'\bEXISTS\s*\(\s*SELECT\b', text, re.IGNORECASE):
            return True
        # 模式2: ((SELECT... — 函数内嵌套括号包裹标量子查询
        if re.search(r'\(\s*\(\s*SELECT\b', text, re.IGNORECASE):
            return True
        # 模式3: IN (SELECT...) 或 NOT IN (SELECT...)
        if re.search(r'\bIN\s*\(\s*SELECT\b', text, re.IGNORECASE):
            return True
        return False

    @staticmethod
    def _find_matching_paren_safe(text: str, start: int) -> int:
        """从 start 位置（必须是 '('）找到匹配的 ')'，跳过字符串字面量。"""
        if start >= len(text) or text[start] != '(':
            return -1
        depth = 0
        in_str = False
        qc = None
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if c == qc:
                    in_str = False
                continue
            if c in ("'", '"'):
                in_str = True
                qc = c
                continue
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _find_scalar_subquery_start(self, text: str) -> int:
        """找到标量子查询起始 '(' 的位置。

        处理：
        - EXISTS(SELECT...) → EXISTS 后的 (
        - NOT EXISTS(SELECT...) → EXISTS 后的 (
        - ((SELECT...) → 内层的 (
        - IN (SELECT...) → IN 后的 (
        """
        # EXISTS 模式
        for m in re.finditer(r'\bEXISTS\s*\(', text, re.IGNORECASE):
            paren_pos = m.end() - 1  # ( 的位置
            rest = text[paren_pos + 1:].lstrip()
            if re.match(r'^SELECT\b', rest, re.IGNORECASE):
                return paren_pos

        # IN (SELECT...) 模式
        for m in re.finditer(r'\bIN\s*\(', text, re.IGNORECASE):
            paren_pos = m.end() - 1
            rest = text[paren_pos + 1:].lstrip()
            if re.match(r'^SELECT\b', rest, re.IGNORECASE):
                return paren_pos

        # ((SELECT...) 模式 — 找内层 (
        for m in re.finditer(r'\(\s*\(\s*SELECT\b', text, re.IGNORECASE):
            # 找内层 (
            inner_start = text.index('(', m.start() + 1)
            return inner_start

        return -1

    def _split_by_top_level_clauses(self, text: str) -> list:
        """按顶层 SQL 子句关键字拆分，忽略括号和字符串内的关键字。

        Returns:
            拆分后的子句列表，每个包含关键字及其后内容。
            如 ['SELECT SUM(x)', 'FROM t', 'WHERE a = 1 AND b = 2']
        """
        clauses = []
        depth = 0
        in_str = False
        qc = None
        current_start = 0
        i = 0

        clause_keywords = [
            'SELECT', 'FROM', 'WHERE', 'INNER JOIN', 'LEFT JOIN',
            'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN', 'JOIN',
            'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT',
            'AND', 'OR', 'ON',
        ]

        while i < len(text):
            c = text[i]
            if in_str:
                if c == qc:
                    in_str = False
                i += 1
                continue
            if c in ("'", '"'):
                in_str = True
                qc = c
                i += 1
                continue
            if c == '(':
                depth += 1
                i += 1
                continue
            if c == ')':
                depth -= 1
                i += 1
                continue

            if depth == 0:
                for kw in clause_keywords:
                    kw_len = len(kw)
                    if i + kw_len > len(text):
                        continue
                    upper_ahead = text[i:i + kw_len].upper()
                    if upper_ahead != kw:
                        continue
                    # 检查边界：关键字前后不能是字母数字或下划线
                    before_ok = (i == 0 or not text[i - 1].isalnum() and text[i - 1] != '_')
                    after_pos = i + kw_len
                    after_ok = (after_pos >= len(text) or not text[after_pos].isalnum() and text[after_pos] != '_')
                    if not (before_ok and after_ok):
                        continue

                    # 对于 AND/OR，需要特殊处理 BETWEEN...AND
                    if kw in ('AND', 'OR'):
                        # 排除 BETWEEN ... AND 模式（简化检测）
                        seg = text[current_start:i].strip().upper()
                        if re.search(r'\bBETWEEN\s+\S+\s*$', seg):
                            continue

                    # 找到子句边界
                    if i > current_start:
                        seg = text[current_start:i].strip()
                        if seg:
                            clauses.append(seg)
                    current_start = i
                    i += kw_len
                    break
                else:
                    i += 1
                    continue
                continue  # matched a keyword, skip normal i += 1
            i += 1

        remaining = text[current_start:].strip()
        if remaining:
            clauses.append(remaining)
        return clauses

    def _format_scalar_subquery_content(self, content: str, indent: int) -> list:
        """将标量子查询内容格式化为多行。

        Args:
            content: 子查询内容（不含外层括号）
            indent: 子查询内容的缩进级别

        Returns:
            格式化后的行列表
        """
        clauses = self._split_by_top_level_clauses(content)
        result = []

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue
            upper = clause.upper()

            # AND/OR 单独缩进
            if re.match(r'^AND\b', upper) or re.match(r'^OR\b', upper):
                # AND/OR 右对齐
                and_or_ind = indent + (2 if upper.startswith('AND') else 1)
                result.append(f"{' ' * and_or_ind}{clause}")
            elif re.match(r'^ON\b', upper):
                result.append(f"{' ' * (indent + 2)}{clause}")
            else:
                result.append(f"{' ' * indent}{clause}")

        return result

    def _expand_scalar_subquery_in_line(self, line: str) -> list:
        """将包含标量子查询的单行拆分为多行。

        处理 EXISTS 和函数内嵌两种模式。
        """
        indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()

        # 找到标量子查询起始位置
        paren_pos = self._find_scalar_subquery_start(stripped)
        if paren_pos == -1:
            return [line]

        # 前缀：子查询 ( 之前的内容
        before = stripped[:paren_pos]
        close_pos = self._find_matching_paren_safe(stripped, paren_pos)
        if close_pos == -1:
            return [line]

        # 后缀：子查询 ) 之后的内容
        after = stripped[close_pos + 1:].strip()

        # 子查询内容（去掉括号）
        subquery_content = stripped[paren_pos + 1:close_pos].strip()

        result = []
        prefix_spaces = ' ' * indent

        # 判断模式
        is_exists = bool(re.search(r'\bEXISTS\s*$', before, re.IGNORECASE))
        is_not_exists = bool(re.search(r'\bNOT\s+EXISTS\s*$', before, re.IGNORECASE))
        is_in = bool(re.search(r'\bIN\s*$', before, re.IGNORECASE))

        if is_exists or is_not_exists or is_in:
            # EXISTS(SELECT...) / IN (SELECT...) 模式
            keyword_before = before.rstrip()
            subquery_indent = indent + len(keyword_before) + 2  # "( " 后缩进

            result.append(f"{prefix_spaces}{keyword_before} (")

            # 格式化子查询内容
            sub_lines = self._format_scalar_subquery_content(
                subquery_content, subquery_indent
            )
            result.extend(sub_lines)

            # 闭括号 + 后续内容
            close_line = f"{prefix_spaces}{' ' * len(keyword_before)}"
            if after:
                close_line += f"){after}"
            else:
                close_line += ")"
            result.append(close_line)
        else:
            # 函数内嵌标量子查询模式（如 AVG(COALESCE((SELECT...), 0))）
            # before 有 N 层未闭合的 (，after 有 N 个 ) + 可选参数和别名
            func_depth = before.count('(') - before.count(')')
            if func_depth <= 0:
                return [line]

            # 输出 before（如 "AVG(COALESCE("）
            result.append(f"{prefix_spaces}{before}")

            # 子查询外层括号 ( — 使用固定缩进增量，避免 len(before) 导致过度缩进
            inner_indent = indent + 4
            result.append(f"{' ' * inner_indent}(")

            # 格式化子查询内容
            content_indent = inner_indent + 4
            sub_lines = self._format_scalar_subquery_content(
                subquery_content, content_indent
            )
            result.extend(sub_lines)

            # 关闭子查询外层括号 )
            result.append(f"{' ' * inner_indent})")

            # 解析 after：提取参数、闭括号、别名
            # after 如 ", 0)) AS category_avg"
            segments = []  # [(type, content)] type: 'param'|'close'|'alias'
            if after:
                current = []
                depth = 0
                in_str = False
                sq = None
                for c in after:
                    if in_str:
                        if c == sq:
                            in_str = False
                        current.append(c)
                        continue
                    if c in ("'", '"'):
                        in_str = True
                        sq = c
                        current.append(c)
                        continue
                    if c == '(':
                        depth += 1
                        current.append(c)
                    elif c == ')':
                        if depth > 0:
                            depth -= 1
                            current.append(c)
                        else:
                            seg = ''.join(current).strip()
                            if seg:
                                segments.append(('param', seg))
                            segments.append(('close', ')'))
                            current = []
                    elif c == ',' and depth == 0:
                        seg = ''.join(current).strip()
                        if seg:
                            segments.append(('param', seg))
                        current = [c]
                    else:
                        current.append(c)
                seg = ''.join(current).strip()
                if seg:
                    if segments and segments[-1][0] == 'close':
                        segments.append(('alias', seg))
                    else:
                        segments.append(('param', seg))

            # 输出参数和闭括号
            close_indent = inner_indent

            for seg_type, seg_content in segments:
                if seg_type == 'param':
                    result.append(f"{' ' * close_indent}{seg_content}")
                elif seg_type == 'close':
                    close_indent = max(indent, close_indent - 4)
                    result.append(f"{' ' * close_indent})")
                elif seg_type == 'alias':
                    if result:
                        result[-1] += f" {seg_content}"

        return result

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
                    # V4 风格后处理（leading comma, AND/OR对齐, CASE WHEN等）
                    fmt = self._apply_v4_full_style(fmt)
                    # 修复 sqlglot 将 'col NOT IN' 改为 'NOT col IN' 的问题
                    fmt = re.sub(
                        r'\bNOT\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s+IN\s*\(',
                        r'\1 NOT IN (',
                        fmt
                    )
                    # 修复子查询括号对齐和内容缩进
                    fmt = self._fix_subquery_indent(fmt)
                    # 拆分超长标量子查询
                    fmt = self._split_long_scalar_subqueries(fmt)
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

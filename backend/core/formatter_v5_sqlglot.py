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

    _STANDALONE_PREFIX = '__STANDALONE_'
    _INLINE_PREFIX = '__INLINE_'

    # sqlglot 会重写的函数名映射（新增函数只需修改此处）
    _FUNC_MAP = {
        'NVL': '___NVL___',
        'SUBSTR': '___SUBSTR___',
        'GET_JSON_OBJECT': '___GJSON___',
    }

    def __init__(self, indent_spaces: int = 4):
        self.indent_spaces = indent_spaces

    # ============================================================
    # Shared utilities: string-aware scanning & keyword boundary
    # ============================================================

    @staticmethod
    def _is_keyword_boundary(text, pos, kw_len):
        """Check if text[pos:pos+kw_len] is a whole-word keyword match.

        Returns True only if the character before is not alphanumeric/underscore
        and the character after is not alphanumeric/underscore.
        """
        before_ok = (pos == 0 or not text[pos - 1].isalnum() and text[pos - 1] != '_')
        after_pos = pos + kw_len
        after_ok = (after_pos >= len(text) or not text[after_pos].isalnum() and text[after_pos] != '_')
        return before_ok and after_ok

    @staticmethod
    def _count_parens(text):
        """Count open/close parentheses in text, skipping string literals.

        Returns (open_count, close_count).
        """
        open_c = close_c = 0
        in_str = False
        qc = None
        for ch in text:
            if in_str:
                if ch == qc:
                    in_str = False
            elif ch in ("'", '"'):
                in_str = True
                qc = ch
            elif ch == '(':
                open_c += 1
            elif ch == ')':
                close_c += 1
        return open_c, close_c

    @staticmethod
    def _find_matching_paren_str(text, start):
        """From start position (must be '('), find matching ')', skipping strings.

        Returns the index of the matching ')', or -1.
        """
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
        - 多注释行且注释之间有 OR/AND: 按注释边界拆分为多行
        """
        result = []
        lines = sql.split('\n')

        for line in lines:
            # 查找 /* ... */ 模式
            pattern = r'/\*\s+(.*?)\s+\*/'
            matches = list(re.finditer(pattern, line))

            # 过滤掉 IN 子句和独立注释占位符
            real_matches = [m for m in matches
                            if not (m.group(1).strip().startswith(self._INLINE_PREFIX)
                                    and m.group(1).strip().endswith('__'))
                            and not (m.group(1).strip().startswith(self._STANDALONE_PREFIX)
                                    and m.group(1).strip().endswith('__'))]

            # 多注释行：检查注释之间是否有 OR/AND，有则拆分
            if len(real_matches) > 1:
                has_or_and_between = False
                for j in range(len(real_matches) - 1):
                    between = line[real_matches[j].end():real_matches[j + 1].start()].strip()
                    if re.match(r'^(AND|OR)\b', between, re.IGNORECASE):
                        has_or_and_between = True
                        break

                if has_or_and_between:
                    indent = line[:len(line) - len(line.lstrip())]
                    split_lines = []
                    last_end = 0
                    for m in real_matches:
                        code_before = line[last_end:m.start()].strip()
                        comment = m.group(1).strip()
                        if code_before:
                            if code_before.endswith(','):
                                code_before = code_before[:-1].strip()
                            split_lines.append(f"{indent}{code_before} --{comment}")
                        last_end = m.end()
                    remaining = line[last_end:].strip()
                    if remaining:
                        split_lines.append(f"{indent}{remaining}")
                    result.extend(split_lines)
                    continue

            # 单注释或无 OR/AND — 原有逻辑
            new_line = line
            for match in reversed(real_matches):
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
                    self._emit_select_columns(result, cols, indent, first_on_select_line=True)
                else:
                    result.append(f"{' ' * indent}SELECT")
                continue

            # === SELECT with first column on same line ===
            if upper.startswith('SELECT '):
                first_col = stripped[7:].rstrip(',')
                first_col_stripped = first_col.strip()

                # SELECT DISTINCT (无列名) — 复用 _collect_indented_cols 正确处理 CASE 块
                if first_col_stripped.upper() == 'DISTINCT':
                    result.append(f"{' ' * indent}SELECT DISTINCT")
                    i += 1
                    cols, i = self._collect_indented_cols(lines, i, indent)
                    if cols:
                        self._emit_select_columns(result, cols, indent, first_on_select_line=False)
                    continue

                # SELECT DISTINCT col1... — 提取 DISTINCT，复用 _collect_indented_cols
                if first_col_stripped.upper().startswith('DISTINCT '):
                    actual_col = first_col_stripped[9:].strip()
                    result.append(f"{' ' * indent}SELECT DISTINCT {actual_col}")
                    i += 1
                    cols, i = self._collect_indented_cols(lines, i, indent)
                    if cols:
                        self._emit_select_columns(result, cols, indent, first_on_select_line=True)
                    continue

                # 普通 SELECT col1...
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
                cols, i = self._collect_indented_cols(lines, i, indent)
                if cols:
                    self._emit_select_columns(result, cols, indent, first_on_select_line=True)
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
                    paren_end = self._find_matching_paren_str(stripped, paren_start)

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
                inner_indent = indent + 4
                comma_prefix = ' ' * inner_indent
                first = True
                while i < len(lines):
                    s = lines[i].strip()
                    si = len(lines[i]) - len(lines[i].lstrip())
                    if not s:
                        i += 1
                        continue
                    # 闭括号结束列定义
                    if s.startswith(')'):
                        result.append(' ' * indent + s)
                        i += 1
                        break
                    col = s.rstrip(',')
                    if first:
                        result.append(f"{comma_prefix}  {col}")
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

            # === WHERE (standalone or with condition) ===
            if upper == 'WHERE' or upper.startswith('WHERE '):
                i = self._handle_condition_clause(lines, i, indent, 'WHERE', 6, result)
                continue

            # === GROUP BY ===
            if upper.startswith('GROUP BY'):
                result, i = self._format_group_order(lines, i, indent, 'GROUP BY', result)
                continue

            # === HAVING (standalone or with condition) ===
            if upper == 'HAVING' or upper.startswith('HAVING '):
                i = self._handle_condition_clause(lines, i, indent, 'HAVING', 7, result)
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

    def _emit_select_columns(self, result, cols, indent, first_on_select_line=True):
        """将 SELECT 列列表输出到 result，正确处理 CASE 块和子查询。

        Args:
            result: 输出行列表
            cols: _collect_indented_cols 返回的列字符串列表
            indent: 基础缩进
            first_on_select_line: 首列是否已输出在 SELECT 行（True=standalone SELECT，
                False=SELECT DISTINCT 等 SELECT 后面已有内容）
        """
        comma_prefix = ' ' * (indent + 5)

        if not cols:
            return

        # 处理第一列
        first_lines = self._format_column_with_case(cols[0])
        if first_lines and re.match(r'^[CWE]\d+\s', first_lines[0]):
            if first_on_select_line:
                result.append(f"{' ' * indent}SELECT")
            self._append_case_inner_lines(result, first_lines, indent)
        elif first_lines and first_lines[0].startswith('S '):
            subquery_str = re.sub(r'^S\s+', '', first_lines[0])
            if first_on_select_line:
                self._append_subquery_col(result, subquery_str, ' ' * indent, indent)
            else:
                self._append_subquery_col(result, subquery_str, comma_prefix, indent)
        else:
            if first_on_select_line:
                result.append(f"{' ' * indent}SELECT {first_lines[0]}")
            else:
                result.append(f"{comma_prefix} {first_lines[0]}")
            if len(first_lines) > 1:
                self._append_case_inner_lines(result, first_lines[1:], indent)

        # 后续列：leading comma
        for c in cols[1:]:
            col_lines = self._format_column_with_case(c)
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
                else:
                    result.append(f"{comma_prefix}, {col_lines[0]}")
                    self._append_case_inner_lines(result, col_lines[1:], indent)

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
            open_count, close_count = self._count_parens(s)

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

    @staticmethod
    def _count_case_end(text):
        """统计文本中 CASE 和 END 关键字的出现次数（跳过字符串内的）。

        Returns:
            (case_count, end_count)
        """
        case_count = 0
        end_count = 0
        in_str = False
        qc = None
        i = 0
        _ikb = SQLFormatterV5._is_keyword_boundary
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
            if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE' and _ikb(text, i, 4):
                case_count += 1
                i += 4
                continue
            if i + 3 <= len(text) and text[i:i + 3].upper() == 'END' and _ikb(text, i, 3):
                end_count += 1
                i += 3
                continue
            i += 1
        return case_count, end_count

    def _collect_case_block(self, lines, start_i, case_indent):
        """收集完整的 CASE 块作为一个字符串，处理嵌套 CASE。

        正确追踪行中出现的 CASE/END（如 THEN CASE、ELSE CASE、
        ELSE CASE WHEN ... END），确保深度不会提前归零。

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

            # 跟踪 CASE/END 深度 — 使用全文搜索而非只匹配行首
            # 这样可以正确追踪 "THEN CASE"、"ELSE CASE" 等行中嵌套的 CASE
            cases, ends = self._count_case_end(s)
            case_depth += cases - ends

            collected.append(s.rstrip(','))

            if case_depth <= 0:
                case_depth = 0
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

    def _handle_condition_clause(self, lines, start_i, indent, keyword, kw_len, result):
        """Handle WHERE/HAVING condition clauses (standalone and with condition).

        Processes both standalone keyword (WHERE / HAVING) and keyword-with-condition
        (WHERE x=1 / HAVING x=1) patterns, then collects continuation lines.

        Args:
            lines: all lines
            start_i: index of the keyword line
            indent: base indent level
            keyword: 'WHERE' or 'HAVING'
            kw_len: length of keyword + space (6 for WHERE, 7 for HAVING)
            result: output list to append to

        Returns:
            next line index after processing
        """
        stripped = lines[start_i].strip()
        upper = stripped.upper()

        if upper == keyword:
            first_cond, i = self._merge_standalone_keyword(lines, start_i + 1, indent)
            if first_cond:
                segments = self._split_and_or_in_line(first_cond)
                result.append(f"{' ' * indent}{keyword} {segments[0]}")
                for seg in segments[1:]:
                    result.append(f"{' ' * (indent + 2)}{seg}")
            else:
                result.append(f"{' ' * indent}{keyword}")
        else:
            cond = stripped[kw_len:]
            segments = self._split_and_or_in_line(cond)
            result.append(f"{' ' * indent}{keyword} {segments[0]}")
            for seg in segments[1:]:
                result.append(f"{' ' * (indent + 2)}{seg}")
            i = start_i + 1

        while i < len(lines):
            s = lines[i].strip()
            si = len(lines[i]) - len(lines[i].lstrip())
            if not s or s == ')' or s.startswith(')'):
                break
            if si <= indent and (self._is_clause_line(s) or s.upper().startswith('SELECT')):
                break
            result.append(f"{' ' * (indent + 2)}{s}")
            i += 1
        return i

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

            if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE':
                if SQLFormatterV5._is_keyword_boundary(text, i, 4):
                    case_depth += 1
                    i += 4
                    continue

            if i + 3 <= len(text) and text[i:i + 3].upper() == 'END':
                if SQLFormatterV5._is_keyword_boundary(text, i, 3):
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
        _ikb = SQLFormatterV5._is_keyword_boundary

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
                if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE' and _ikb(text, i, 4):
                    case_depth += 1
                    i += 4
                    continue

                if i + 3 <= len(text) and text[i:i + 3].upper() == 'END' and _ikb(text, i, 3):
                    case_depth -= 1
                    i += 3
                    continue

                if case_depth == 0 and i + 4 <= len(text) and text[i:i + 4].upper() == 'ELSE' and _ikb(text, i, 4):
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
        _ikb = SQLFormatterV5._is_keyword_boundary

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
                if i + 4 <= len(text) and text[i:i + 4].upper() == 'CASE' and _ikb(text, i, 4):
                    case_depth += 1
                    i += 4
                    continue

                if i + 3 <= len(text) and text[i:i + 3].upper() == 'END' and _ikb(text, i, 3):
                    case_depth -= 1
                    i += 3
                    continue

                if case_depth == 0 and i + 4 <= len(text) and text[i:i + 4].upper() == 'WHEN' and _ikb(text, i, 4):
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

    def _extract_partitioned_by(self, sql: str) -> tuple:
        """提取 PARTITIONED BY 子句的原始列定义信息。

        sqlglot 会将分区列合并到主列定义并丢失原始类型和注释。
        本方法在 sqlglot 处理前提取原始信息，供后处理恢复。

        Returns:
            (sql, partition_info) — partition_info 为 list[(name, type, comment)] 或 None
        """
        m = re.search(r'\bPARTITIONED\s+BY\s*\(', sql, re.IGNORECASE)
        if not m:
            return sql, None

        paren_start = m.end() - 1
        paren_end = self._find_matching_paren_str(sql, paren_start)
        if paren_end == -1:
            return sql, None

        content = sql[paren_start + 1:paren_end].strip()
        if not content:
            return sql, None

        # 用引号感知的分割方法
        cols = self._split_set_columns(content)
        partition_info = []
        for col in cols:
            col = col.strip()
            p = self._parse_col_def(col)
            if p:
                partition_info.append(p)

        return sql, partition_info if partition_info else None

    def _restore_partitioned_by(self, text: str, partition_info: list) -> str:
        """恢复 PARTITIONED BY 子句的原始内联定义，并从主列中移除分区列。

        partition_info: [(name, type, comment), ...] — 预处理时提取的原始分区列定义
        """
        if not partition_info:
            return text
        partition_names = {p[0].upper() for p in partition_info}

        # 找到主列定义的 ( ... ) 块
        create_match = re.search(r'\bCREATE\s+TABLE\b', text, re.IGNORECASE)
        if not create_match:
            return text

        # 找到主列 ( 的位置
        rest = text[create_match.start():]
        paren_start_rel = rest.index('(')
        paren_start = create_match.start() + paren_start_rel
        paren_end = self._find_matching_paren_str(text, paren_start)
        if paren_end == -1:
            return text

        # 解析主列内容，移除分区列
        col_content = text[paren_start + 1:paren_end]
        col_lines = col_content.split('\n')
        kept_lines = []
        for cl in col_lines:
            cl_stripped = cl.strip()
            if not cl_stripped:
                kept_lines.append(cl)
                continue
            # 去掉前导逗号
            col_def = cl_stripped.lstrip(', ').strip()
            p = self._parse_col_def(col_def)
            if p and p[0].upper() in partition_names:
                continue  # 跳过分区列
            kept_lines.append(cl)

        # 重建主列内容（去掉尾部空行）
        while kept_lines and not kept_lines[-1].strip():
            kept_lines.pop()

        new_col_content = '\n'.join(kept_lines)
        before = text[:paren_start + 1]
        after_paren = text[paren_end + 1:]

        # 找到 PARTITIONED BY 并替换
        part_match = re.search(r'\n\s*PARTITIONED\s+BY\s*\([^)]*\)', after_paren, re.IGNORECASE | re.DOTALL)
        if not part_match:
            return before + new_col_content + ')' + after_paren

        # 构建对齐的 PARTITIONED BY
        max_name = max(len(p[0]) for p in partition_info)
        max_type = max(len(p[1]) for p in partition_info if p[1])

        part_lines = []
        indent = len(text[:paren_start]) - len(text[:paren_start].lstrip())
        inner_indent = indent + 4
        comma_prefix = ' ' * (indent + 2)
        for j, (name, typ, suffix) in enumerate(partition_info):
            name_pad = name.ljust(max_name)
            parts = name_pad
            if typ:
                parts += f"  {typ.ljust(max_type)}"
            if suffix:
                parts += f"  {suffix}"
            if j == 0:
                part_lines.append(f"{' ' * inner_indent}{parts}")
            else:
                part_lines.append(f"{comma_prefix}, {parts}")

        new_part = '\n' + ' ' * indent + 'PARTITIONED BY (\n' + '\n'.join(part_lines) + '\n' + ' ' * indent + ')'
        new_after = after_paren[:part_match.start()] + new_part + after_paren[part_match.end():]

        # 主列的 ) 独立一行，与 CREATE TABLE 缩进对齐
        base_indent = len(text[:create_match.start()]) - len(text[:create_match.start()].lstrip())
        return before + new_col_content + '\n' + ' ' * base_indent + ')' + new_after

    def _align_create_table_columns(self, text: str) -> str:
        """对齐 CREATE TABLE 列定义：列名、类型、COMMENT 上下对齐。"""
        # Short-circuit: no CREATE TABLE in text
        if 'CREATE TABLE' not in text.upper():
            return text

        lines = text.split('\n')
        result = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            upper = stripped.upper()

            if upper.startswith('CREATE TABLE') and '(' in stripped and stripped.endswith('('):
                block_lines = [lines[i]]
                i += 1
                paren_depth = 1
                while i < len(lines) and paren_depth > 0:
                    o, c = self._count_parens(lines[i])
                    paren_depth += o - c
                    block_lines.append(lines[i])
                    i += 1
                aligned = self._align_col_block(block_lines)
                result.extend(aligned)
                continue

            # 单行 CREATE TABLE (... ) 格式
            if upper.startswith('CREATE TABLE') and '(' in stripped and not stripped.endswith('('):
                paren_start = stripped.index('(')
                before_paren = stripped[:paren_start].rstrip()
                last_word = before_paren.split()[-1].upper() if before_paren.split() else ''
                skip_keywords = {'PARTITION', 'PARTITIONED', 'TBLPROPERTIES', 'BY'}
                if last_word not in skip_keywords:
                    paren_end = self._find_matching_paren_str(stripped, paren_start)
                    if paren_end > paren_start:
                        cols = self._split_set_columns(stripped[paren_start + 1:paren_end])
                        if len(cols) >= 2:
                            aligned = self._align_col_block(lines[i:i + 1], force_single_line=stripped)
                            result.extend(aligned)
                            i += 1
                            continue

            result.append(lines[i])
            i += 1

        return '\n'.join(result)

    def _align_col_block(self, block_lines: list, force_single_line: str = None) -> list:
        """对齐一个 CREATE TABLE 列定义块。

        Args:
            block_lines: 包含 CREATE TABLE 行到 ) 行的所有行
            force_single_line: 如果提供，从该单行中提取列定义
        """
        if force_single_line:
            stripped = force_single_line.strip()
            indent = force_single_line[:len(force_single_line) - len(force_single_line.lstrip())]
            paren_start = stripped.index('(')
            paren_end = self._find_matching_paren_str(stripped, paren_start)
            if paren_end == -1:
                return block_lines

            cols = self._split_set_columns(stripped[paren_start + 1:paren_end])
            if not cols:
                return block_lines

            parsed = [p for col in cols if (p := self._parse_col_def(col.strip()))]
            if len(parsed) < 2:
                return block_lines

            header_lines = [f'{indent}{stripped[:paren_start]}', f'{indent}(']
            footer_lines = [f'{indent}){stripped[paren_end + 1:].strip()}']
            return self._format_aligned_cols(parsed, header_lines, footer_lines, len(indent))

        # 多行格式 — 解析列定义行
        parsed = []
        header_line = None
        footer_lines = []
        in_cols = False

        for bl in block_lines:
            s = bl.strip()
            if s.upper().startswith('CREATE TABLE'):
                header_line = bl
                in_cols = True
                continue
            if s.startswith(')'):
                footer_lines.append(bl)
                in_cols = False
                continue
            if not in_cols or not s:
                if not in_cols:
                    footer_lines.append(bl)
                continue
            col_def = s.lstrip(', ').strip() if s.startswith(',') else s.strip()
            p = self._parse_col_def(col_def)
            if p:
                parsed.append(p)
            else:
                footer_lines.append(bl)

        if len(parsed) < 2:
            return block_lines

        indent = len(block_lines[0]) - len(block_lines[0].lstrip()) if block_lines[0].strip() else 0
        header_lines = [header_line] if header_line else []
        return self._format_aligned_cols(parsed, header_lines, footer_lines, indent)

    @staticmethod
    def _format_aligned_cols(parsed: list, header_lines: list, footer_lines: list, indent: int) -> list:
        """格式化对齐后的列定义行。

        parsed: [(name, type, suffix), ...]
        header_lines: CREATE TABLE 行等前缀行
        footer_lines: ) 及后续行
        indent: 基础缩进空格数
        """
        max_name = max(len(p[0]) for p in parsed)
        max_type = max(len(p[1]) for p in parsed if p[1])
        comma_prefix = ' ' * (indent + 2)

        result = list(header_lines)
        for j, (name, typ, suffix) in enumerate(parsed):
            parts = name.ljust(max_name)
            if typ:
                parts += f"  {typ.ljust(max_type)}"
            if suffix:
                parts += f"  {suffix}"
            if j == 0:
                result.append(f"{comma_prefix}  {parts}")
            else:
                result.append(f"{comma_prefix}, {parts}")
        result.extend(footer_lines)
        return result

    @staticmethod
    def _parse_col_def(col_def: str):
        """解析单个列定义，返回 (name, type, suffix) 或 None。

        支持格式：
        - ACTIONTYPE VARCHAR(1) COMMENT '操作类型'
        - BUOCMONTH DECIMAL(6, 0) COMMENT '报告期'
        - DATA_DT STRING
        - col1 INT
        """
        col_def = col_def.strip()
        if not col_def:
            return None

        # 匹配：列名 + 类型(可选括号参数) + 后缀(COMMENT等)
        m = re.match(
            r'(\w+)\s+(\w+(?:\s*\([^)]*\))?)\s*(.*)',
            col_def,
            re.IGNORECASE | re.DOTALL
        )
        if m:
            name = m.group(1)
            typ = m.group(2)
            suffix = m.group(3).strip()
            return (name, typ, suffix)

        # 只有列名（无类型）
        m2 = re.match(r'(\w+)\s*$', col_def)
        if m2:
            return (m2.group(1), '', '')

        return None

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
    def _preserve_standalone_comments(sql, start_counter=0):
        """预处理：将被注释掉的SQL代码行（-- WHEN ... THEN ...）转为 /* __STANDALONE_N__ */
        占位符附在 THEN 值后。sqlglot 会保留 THEN 值后的 /* */ 注释。

        Args:
            sql: 原始SQL文本
            start_counter: 起始计数器（避免多语句间占位符名冲突）

        Returns:
            (cleaned_sql, comment_map, next_counter)
        """
        lines = sql.split('\n')
        comment_map = {}
        counter = start_counter
        result_lines = []
        last_content_idx = -1
        # 延迟附着：orig_line_idx -> [placeholder, ...]
        deferred = {}

        def _insert_before_comment(text, placeholder):
            """在 text 的 -- 行注释之前插入 /* placeholder */ """
            in_str = False
            for k in range(len(text) - 1):
                if text[k] == "'" and (k == 0 or text[k - 1] != '\\'):
                    in_str = not in_str
                elif text[k:k + 2] == '--' and not in_str:
                    return f'{text[:k].rstrip()} /* {placeholder} */ {text[k:]}'
            return f'{text} /* {placeholder} */'

        for i, line in enumerate(lines):
            stripped = line.strip()
            is_standalone = (stripped.startswith('--')
                    and re.match(
                        r'^--\s*(WHEN|CASE|SELECT|THEN|ELSE|END|AND|OR|FROM|WHERE)\b',
                        stripped, re.IGNORECASE))

            if is_standalone:
                placeholder = f'{SQLFormatterV5._STANDALONE_PREFIX}{counter}__'
                comment_map[placeholder] = stripped
                counter += 1

                if last_content_idx >= 0:
                    prev_stripped = result_lines[last_content_idx].strip()
                    attached = False
                    # 裸 CASE（无 THEN）后 sqlglot 会移走 /* */，需延迟附着到前方 THEN 行
                    if (re.match(r'^CASE\b', prev_stripped, re.IGNORECASE)
                            and not re.search(r'\bTHEN\b', prev_stripped, re.IGNORECASE)):
                        for j in range(i + 1, len(lines)):
                            ns = lines[j].strip()
                            if not ns or ns.startswith('--'):
                                continue
                            if re.match(r'^END\b', ns, re.IGNORECASE):
                                break
                            if re.search(r'\bTHEN\b', ns, re.IGNORECASE):
                                deferred.setdefault(j, []).append(placeholder)
                                attached = True
                                break
                    if not attached:
                        result_lines[last_content_idx] = _insert_before_comment(
                            result_lines[last_content_idx], placeholder)
            else:
                # 检查此行是否有延迟附着的占位符
                if i in deferred:
                    for ph in deferred[i]:
                        line = _insert_before_comment(line, ph)

                result_lines.append(line)
                if stripped and not stripped.startswith('--'):
                    last_content_idx = len(result_lines) - 1

        return '\n'.join(result_lines), comment_map, counter

    @staticmethod
    def _restore_standalone_placeholders(text, comment_map):
        """后处理：将 /* __STANDALONE_N__ */ 占位符替换为原始注释，拆到独立行。"""
        if not comment_map:
            return text

        lines = text.split('\n')
        result = []

        for line in lines:
            clean = line
            originals = []
            for placeholder, original in comment_map.items():
                marker = f'/* {placeholder} */'
                if marker in clean:
                    clean = clean.replace(marker, '')
                    originals.append(original)

            if originals:
                indent = line[:len(line) - len(line.lstrip())]
                clean = clean.rstrip()
                if clean.strip():
                    result.append(clean)
                for original in originals:
                    result.append(indent + original)
            else:
                result.append(line)

        return '\n'.join(result)

    @staticmethod
    def _split_merged_comment_lines(text):
        """拆分被sqlglot合并的注释行。

        sqlglot会将多条独立注释合并到同一行，例如：
            --全部放到一张表里面  -----信贷客户插入目标表
        应拆分为：
            --全部放到一张表里面
            -----信贷客户插入目标表

        检测模式：行以 -- 开头（可选前导空格），中间出现 3个以上连续短横线
        的注释头（如 -----、-------）。
        """
        lines = text.split('\n')
        result = []
        for line in lines:
            stripped = line.strip()
            # 只处理纯注释行（以 -- 开头）
            if not stripped.startswith('--'):
                result.append(line)
                continue
            indent = line[:len(line) - len(line.lstrip())]
            # 检测行内是否包含第二个注释标记（3+短横线，前面有2+空格）
            # 模式: --comment1  ---comment2  (至少2个空格 + 3+短横线)
            parts = re.split(r'\s{2,}(-{3,}.*)$', stripped, maxsplit=1)
            if len(parts) == 3:
                result.append(f'{indent}{parts[0]}')
                result.append(f'{indent}{parts[1]}')
            else:
                result.append(line)
        return '\n'.join(result)

    @staticmethod
    def _split_in_values_with_comments(in_content, comment_map=None):
        """将 IN 子句内容按值拆分，正确处理值和注释的关联。

        支持两种注释格式：
        - /* __INLINE_N__ */ 占位符（来自预处理，comment_map 不为空时使用）
        - --comment 行注释（已恢复的格式，comment_map 为空时使用）

        输出示例：["'AAA'", "'BBB' --comment1", "'CCC' --comment2"]
        """
        parts = []
        i = 0
        n = len(in_content)
        while i < n:
            # 跳过逗号和空白
            while i < n and in_content[i] in (' ', ',', '\t'):
                i += 1
            if i >= n:
                break
            # 期望一个字符串值 'xxx'
            if in_content[i] != "'":
                i += 1
                continue
            # 找到字符串结束
            j = i + 1
            while j < n and in_content[j] != "'":
                j += 1
            if j >= n:
                break
            value = in_content[i:j + 1]  # 包含引号
            i = j + 1
            # 跳过逗号和空白（逗号可能在值和注释之间，如 'val', /* comment */）
            while i < n and in_content[i] in (' ', ',', '\t'):
                i += 1
            # 检查注释：先检查 /* __INLINE_N__ */ 占位符
            comment = ''
            if comment_map and in_content[i:i + 2] == '/*':
                end_star = in_content.find('*/', i + 2)
                if end_star != -1:
                    placeholder_text = in_content[i + 2:end_star].strip()
                    if placeholder_text.startswith('__INLINE_') and placeholder_text.endswith('__'):
                        # 找到占位符，替换为原始注释
                        comment = comment_map.get(placeholder_text, '')
                        i = end_star + 2
            # 如果没有 /* */ 占位符，检查 --comment
            if not comment and i < n and in_content[i:i + 2] == '--':
                k = i + 2
                # 注释持续到下一个 ' 开头（下一个值的开始）或到结尾
                while k < n and in_content[k] != "'":
                    k += 1
                comment = in_content[i:k].rstrip()
                i = k
            if comment:
                parts.append(f"{value} {comment}")
            else:
                parts.append(value)
        return parts

    def _split_in_clause_comments(self, text, comment_map=None):
        """拆分 IN 子句中被sqlglot合并的注释值。

        处理两种情况：
        1. /* __INLINE_N__ */ 占位符（CASE WHEN 中被折叠到一行的 IN 子句）
        2. --comment 行注释（简单 WHERE IN 子句）

        两种情况都拆分为每个值+注释独立一行，使用 leading comma 风格。
        对于占位符情况，同时将 /* __INLINE_N__ */ 替换为 --原始注释。
        """
        lines = text.split('\n')
        result = []
        for line in lines:
            stripped = line.strip()

            # 查找 IN ( 的位置（大小写不敏感）
            in_match = re.search(r'\bIN\s*\(', stripped, re.IGNORECASE)
            if not in_match:
                result.append(line)
                continue

            # 找到 IN( 内部匹配的 )
            paren_start = in_match.end() - 1  # ( 的位置
            paren_end = self._find_matching_paren_str(stripped, paren_start)
            if paren_end == -1:
                result.append(line)
                continue

            # 提取 IN 子句内容
            in_content = stripped[paren_start + 1:paren_end].strip()
            after_paren = stripped[paren_end + 1:].strip()

            # 检查是否需要拆分：/* __INLINE_ */ 占位符 或 多处 -- 注释
            has_inline_placeholders = (
                comment_map
                and re.search(r'/\*\s*__INLINE_\d+__\s*\*/', in_content)
            )
            dash_comment_count = len(re.findall(r'--', in_content))

            if not has_inline_placeholders and dash_comment_count < 2:
                result.append(line)
                continue

            # 拆分策略：按 'value' 模式逐个提取，每个值后可选跟注释
            parts = self._split_in_values_with_comments(in_content, comment_map)
            if len(parts) < 2:
                result.append(line)
                continue

            # 构建拆分后的输出
            indent = line[:len(line) - len(line.lstrip())]
            prefix = stripped[:paren_start + 1]  # 包括 (
            value_indent = ' ' * len(prefix)

            output_parts = []
            for pi, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                if pi == 0:
                    output_parts.append(part)
                else:
                    output_parts.append(',' + part)

            if output_parts:
                result.append(f'{indent}{prefix}{output_parts[0]}')
                for op in output_parts[1:]:
                    result.append(f'{indent}{value_indent}{op}')
                paren_align = ' ' * paren_start
                if after_paren:
                    result.append(f'{indent}{paren_align}){after_paren}')
                else:
                    result.append(f'{indent}{paren_align})')
            else:
                result.append(line)

        return '\n'.join(result)

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
        _ikb = SQLFormatterV5._is_keyword_boundary

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

            if depth == 0 and content[i:i + 4].upper() == 'CASE' and _ikb(content, i, 4):
                case_depth += 1
                i += 4
                continue
            if depth == 0 and case_depth > 0 and content[i:i + 3].upper() == 'END' and _ikb(content, i, 3):
                case_depth -= 1
                i += 3
                continue

            if depth == 0 and case_depth == 0:
                if content[i:i + 4].upper() == 'THEN' and _ikb(content, i, 4):
                    seg = content[seg_start:i].strip()
                    if seg:
                        result.append(seg)
                    seg_start = i
                    i += 4
                    continue
                if i > seg_start and content[i:i + 4].upper() == 'WHEN' and _ikb(content, i, 4):
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
        paren_depths = set()  # 追踪哪些深度有 ( 需要匹配 )

        for idx, line in enumerate(merged):
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()

            # 跟踪嵌套 CASE 深度 — 使用全文搜索追踪 CASE/END
            cases_here, ends_here = self._count_case_end(stripped)

            # 纯 CASE 行（行首 CASE，无 END）
            if re.match(r'\bCASE\b', upper) and cases_here > 0 and ends_here == 0:
                case_depth += 1
                result.append(f"C{case_depth} {stripped}")
                continue

            # 纯 END 行（行首 END）
            if re.match(r'\bEND\b', upper):
                depth_for_end = case_depth
                result.append(f"E{case_depth} {stripped}")
                case_depth = max(0, case_depth - 1)
                # 如果这个深度有匹配的 (，检查下一行是否已有 )
                # 如果下一行是 ) 或 )--comment，留给后面的 P 标记处理
                # 否则自动补 )
                if depth_for_end in paren_depths:
                    # 检查下一行是否是 ) 开头
                    has_existing_paren = False
                    if idx + 1 < len(merged):
                        next_s = merged[idx + 1].strip()
                        if re.match(r'^\)\s*(?:--.*)?$', next_s):
                            has_existing_paren = True
                    if not has_existing_paren:
                        result.append(f"P{depth_for_end} )")
                        paren_depths.discard(depth_for_end)
                continue

            # 行内包含 CASE...END（如 ELSE CASE WHEN ... END、THEN CASE WHEN ... END）
            if cases_here > 0 and ends_here > 0:
                self._expand_embedded_case(result, stripped, case_depth)
                # 更新深度：行内净CASE数量
                case_depth += cases_here - ends_here
                continue

            # 行内有 CASE 但无 END（如 THEN CASE、ELSE CASE）
            # 拆分为 THEN ( / ELSE ( + 换行 + CASE，追踪括号
            if cases_here > 0 and ends_here == 0:
                before_case = stripped[:re.search(r'\bCASE\b', stripped, re.IGNORECASE).start()].strip()
                case_depth += 1
                if before_case and before_case.upper() in ('THEN', 'ELSE'):
                    result.append(f"W{case_depth - 1} {before_case} (")
                    paren_depths.add(case_depth)
                else:
                    result.append(f"W{case_depth - 1} {before_case}" if before_case else "")
                result.append(f"C{case_depth} CASE")
                continue

            # 闭括号行: ) 或 )--comment（原始 SQL 中自带的）
            if re.match(r'^\)\s*(?:--.*)?$', stripped):
                # 找到匹配的 ( 所在的深度
                if case_depth + 1 in paren_depths:
                    result.append(f"P{case_depth + 1} {stripped}")
                    paren_depths.discard(case_depth + 1)
                else:
                    result.append(f"P{max(case_depth, 1)} {stripped}")
                continue

            # WHEN/THEN/ELSE 等内容行
            # 如果同一行包含 WHEN...THEN，拆分为独立段
            if re.match(r'\bWHEN\b', upper) and re.search(r'\bTHEN\b', upper):
                segments = self._split_when_then(stripped)
                for seg in segments:
                    result.append(f"W{case_depth} {seg}")
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
        # 允许 END 后面跟 )、注释（--...）和空白
        end_match = re.search(r'\bEND\b(?=\)*\s*(?:--.*)?$)', stripped, re.IGNORECASE)

        if not (case_match and end_match):
            result.append(f"W{depth} {stripped}")
            return

        before = stripped[:case_match.start()].strip()
        inner_case = stripped[case_match.start():end_match.end()]
        after = stripped[end_match.end():].strip()

        has_paren = False
        if before:
            # 检测 before 中是否包含 ( — 如 THEN (、ELSE (、或独立的 (
            paren_in_before = before.endswith('(')
            clean_before = before[:-1].strip() if paren_in_before else before
            # THEN/ELSE 后跟嵌套 CASE 时，添加 ( 并追踪
            if clean_before.upper() in ('THEN', 'ELSE'):
                result.append(f"W{depth} {clean_before} (")
                has_paren = True
            elif paren_in_before:
                # ( 直接在 CASE 前面，如 (CASE WHEN ...
                result.append(f"W{depth} {before}")
                has_paren = True
            else:
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
        if has_paren:
            result.append(f"P{inner_depth} )")
        elif after:
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

    def _append_w_line(self, result, content, when_indent):
        """Append a W-type line (WHEN/THEN/ELSE/AND/OR) with AND/OR splitting.

        Handles AND/OR right-alignment and long-line splitting.
        """
        content_upper = content.upper().lstrip()
        if re.match(r'\b(AND|OR)\b', content_upper):
            result.append(f"{' ' * self._and_or_indent(when_indent, content)}{content}")
        else:
            output_line = f"{' ' * when_indent}{content}"
            if len(output_line) > 250:
                segments = self._split_and_or_in_line(content)
                if len(segments) > 1:
                    result.append(f"{' ' * when_indent}{segments[0]}")
                    for seg in segments[1:]:
                        result.append(f"{' ' * self._and_or_indent(when_indent, seg)}{seg}")
                    return
            result.append(output_line)

    def _append_case_inner_lines(self, result, inner_lines, indent):
        """将 CASE WHEN 内部行（WHEN/ELSE/END）添加到结果中，正确处理缩进。

        支持两种输入格式：
        1. 带标记的多行 CASE 块（来自 _format_multiline_case_block）：
           'C{depth} ...' / 'W{depth} ...' / 'E{depth} ...' / 'P{depth} ...'
        2. 纯文本行（来自 _format_case_when_single）：
           无标记，按 WHEN/ELSE/END 关键字判断

        缩进规则（基于列的 leading comma 位置，每层 WHEN +10）：
        - depth=1: CASE/END = indent + 7, WHEN/THEN/ELSE = indent + 11 (CASE+4)
        - depth>1: WHEN/THEN/ELSE = indent + 11 + (depth-1)*10, CASE/END = WHEN - 4
        - 嵌套 CASE 在 ( 后: CASE = ( + 1, 即 WHEN + 6
        - AND/OR 续行: 右对齐上面关键字 (WHEN+1 / WHEN+2)
        - P 标记: 闭括号，与同深度 CASE/END 对齐减1格
        """
        base_case = indent + 7   # depth=1 CASE/END 基础缩进

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

                # 每层 WHEN 固定 +10，d1 = CASE+4, d>=2 = WHEN-4
                if depth == 1:
                    case_indent = base_case
                    when_indent = base_case + 4
                else:
                    when_indent = indent + 11 + (depth - 1) * 10
                    case_indent = when_indent - 4

                if marker_type == 'C' or marker_type == 'E':
                    result.append(f"{' ' * case_indent}{content}")
                elif marker_type == 'P':
                    result.append(f"{' ' * (case_indent - 1)}{content}")
                else:
                    self._append_w_line(result, content, when_indent)
            else:
                # 纯文本行（单行 CASE 拆分结果）
                if stripped.startswith('END'):
                    result.append(f"{' ' * base_case}{stripped}")
                else:
                    self._append_w_line(result, stripped, base_case + 4)

    def _preprocess_in_clause_comments(self, sql: str) -> tuple:
        """预处理 IN 子句中紧跟在值后面的 -- 注释。

        sqlglot 无法解析 'value'--comment 这种写法（值引号后紧跟行注释）。
        将其转换为 'value' /*__INLINE_N__*/ 格式，让 sqlglot 可以正确解析。

        同时处理 NOT IN 子句。

        Returns:
            (processed_sql, comment_map) — comment_map 用于后处理恢复
        """
        comment_map = {}
        counter = 0

        # 使用状态机找到 IN (... 'value'--comment ...) 模式
        # 策略：找到 IN ( 或 NOT IN ( 位置，然后在括号内
        # 将 'xxx'--comment 替换为 'xxx' /*__INLINE_N__*/
        result = list(sql)
        offset = 0

        i = 0
        while i < len(sql):
            # 查找 IN ( 或 NOT IN ( 模式
            # 手动检查左侧词边界：如果前一个字符是字母/数字/下划线，
            # 说明 IN 是单词内部（如 JOIN、DISTINCT、BEGIN），跳过
            if i > 0 and (sql[i - 1].isalnum() or sql[i - 1] == '_'):
                i += 1
                continue

            upper_rest = sql[i:].upper()
            in_match = re.match(r'(IN|NOT\s+IN)\s*\(', upper_rest)
            if not in_match:
                i += 1
                continue

            # 找到 ( 的位置
            paren_pos = i + in_match.end() - 1  # ( 在原始 sql 中的位置

            # 找到匹配的 )
            paren_end = self._find_matching_paren_str(sql, paren_pos)
            if paren_end == -1:
                i += 1
                continue

            # 在 IN (...) 内部，将 'value'--comment 替换为 'value' /*__INLINE_N__*/
            in_content = sql[paren_pos + 1:paren_end]
            new_in_content = self._replace_inline_comments_in_in_clause(in_content, comment_map, counter)
            if new_in_content != in_content:
                # 计算新的 counter 值
                counter = len(comment_map)
                # 替换
                result_list = list(sql[:paren_pos + 1]) + list(new_in_content) + list(sql[paren_end:])
                sql = ''.join(result_list)
                # 重新计算 paren_end 因为内容变了
                new_paren_end = paren_pos + 1 + len(new_in_content)
                i = new_paren_end + 1
            else:
                i = paren_end + 1

        return sql, comment_map

    def _replace_inline_comments_in_in_clause(self, content: str, comment_map: dict, start_counter: int) -> str:
        """替换 IN 子句内容中紧跟在值后面的 -- 注释为 /* */ 格式。

        将 'value'--comment 替换为 'value' /*__INLINE_N__*/
        """
        counter = start_counter
        result = []
        i = 0
        in_str = False
        qc = None

        while i < len(content):
            ch = content[i]

            # 字符串内
            if in_str:
                result.append(ch)
                if ch == qc:
                    in_str = False
                i += 1
                continue

            # 进入字符串
            if ch in ("'", '"'):
                in_str = True
                qc = ch
                result.append(ch)
                i += 1
                continue

            # 跳过 /* */ 注释
            if ch == '/' and i + 1 < len(content) and content[i + 1] == '*':
                end = content.find('*/', i + 2)
                if end != -1:
                    result.append(content[i:end + 2])
                    i = end + 2
                    continue

            # 检测 -- 注释（紧跟在值后面）
            if ch == '-' and i + 1 < len(content) and content[i + 1] == '-':
                # 找到注释的结束（到行尾或到下一个引号值）
                # 注释持续到行尾或到 , 或到 )
                comment_start = i
                j = i + 2
                while j < len(content):
                    if content[j] == '\n':
                        break
                    # 如果遇到逗号且后面跟着引号值，注释结束
                    if content[j] == ',':
                        # 检查逗号后面是否有引号值
                        rest = content[j + 1:].lstrip()
                        if rest and rest[0] in ("'", '"'):
                            break
                    j += 1

                comment_text = content[comment_start:j].strip()
                # 如果注释以逗号结尾，去掉逗号（逗号是分隔符不是注释的一部分）
                trailing_comma = ''
                if comment_text.endswith(','):
                    trailing_comma = ','
                    comment_text = comment_text[:-1].strip()

                placeholder = f'__INLINE_{counter}__'
                comment_map[placeholder] = comment_text
                result.append(f' /*{placeholder}*/')
                if trailing_comma:
                    result.append(trailing_comma)
                counter += 1
                i = j
                continue

            result.append(ch)
            i += 1

        return ''.join(result)

    def _restore_in_clause_comments(self, text: str, comment_map: dict) -> str:
        """恢复 IN 子句中被预处理的注释。

        _convert_block_comments_to_line_comments 会将 /*__INLINE_N__*/ 转为 --__INLINE_N__。
        本方法将其恢复为原始的 --comment 内容。

        关键：替换为 --comment 后，如果行内还有后续内容（如另一个值），
        必须在注释后插入换行，否则 -- 会把后续内容变成注释。

        Args:
            text: 格式化后的 SQL
            comment_map: 预处理时生成的映射 {placeholder: original_comment}
        """
        if not comment_map:
            return text

        for placeholder, original_comment in comment_map.items():
            # _convert_block_comments_to_line_comments 会输出 --__INLINE_N__
            text = self._safe_replace_inline_comment(text, f'--{placeholder}', original_comment)
            # 也可能保留为 /* */ 格式（sqlglot 可能加空格：/* __INLINE_N__ */）
            text = self._safe_replace_inline_comment(text, f'/* {placeholder} */', original_comment)
            text = self._safe_replace_inline_comment(text, f'/*{placeholder}*/', original_comment)

        return text

    @staticmethod
    def _safe_replace_inline_comment(text: str, pattern: str, replacement: str) -> str:
        """安全替换行内注释，确保 --comment 后的代码不会被吞掉。

        如果 replacement 是 --comment 格式且 pattern 后面紧跟非空白字符，
        在 replacement 后插入换行符防止后续代码被注释掉。
        """
        while pattern in text:
            idx = text.index(pattern)
            after_idx = idx + len(pattern)
            after_char = text[after_idx] if after_idx < len(text) else ''

            if replacement.startswith('--') and after_char and after_char not in (' ', '\t', '\n', '\r'):
                # 注释后紧跟代码，插入换行防止吞掉
                text = text[:idx] + replacement + '\n' + text[after_idx:]
            else:
                text = text[:idx] + replacement + text[after_idx:]
        return text

    def _escape_dollar_signs(self, sql: str) -> tuple:
        """转义特殊符号（sqlglot 可能误解析）

        转义 $ 符号和 {} 变量语法
        """
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
                        has_comment = '--' in stripped or '--' in next_s
                        while open_p > 0 and k < len(lines):
                            ns = lines[k].strip()
                            if not ns:
                                k += 1
                                continue
                            if '--' in ns:
                                has_comment = True
                            open_p += ns.count('(') - ns.count(')')
                            merged_line += ' ' + ns
                            k += 1
                        # 如果合并链中含 -- 注释，不合并（注释会吞掉后续内容）
                        if has_comment:
                            result.append(line)
                            i += 1
                            continue
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
            o, c = self._count_parens(stripped)
            paren_depth = o - c

            j = i + 1
            while j < len(lines) and paren_depth > 0:
                s = lines[j].strip()
                o, c = self._count_parens(s)
                paren_depth += o - c
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
                    if not self._is_keyword_boundary(text, i, kw_len):
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
        close_pos = self._find_matching_paren_str(stripped, paren_pos)
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
        # 恢复 {} 变量语法 - 非贪婪匹配任意字符
        sql = re.sub(r'___BRACE_OPEN___(.*?)___BRACE_CLOSE___', r'{\1}', sql)
        # 恢复 $ 符号
        sql = re.sub(r'___DOLLAR___', '$', sql)
        return sql

    @staticmethod
    def _escape_functions(sql: str) -> tuple:
        """将 sqlglot 会重写的函数名替换为占位符。

        只替换代码中的函数调用，跳过字符串和注释内的。
        函数名映射见 _FUNC_MAP 类属性。
        """
        func_map = SQLFormatterV5._FUNC_MAP
        result = []
        i = 0
        found = set()
        in_str = False
        qc = None
        in_line_comment = False
        in_block_comment = False

        while i < len(sql):
            ch = sql[i]

            if in_line_comment:
                result.append(ch)
                if ch == '\n':
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                result.append(ch)
                if ch == '*' and i + 1 < len(sql) and sql[i + 1] == '/':
                    in_block_comment = False
                i += 1
                continue

            if in_str:
                result.append(ch)
                if ch == '\\' and i + 1 < len(sql):
                    result.append(sql[i + 1])
                    i += 2
                    continue
                if ch == qc:
                    in_str = False
                i += 1
                continue

            if ch in ("'", '"'):
                in_str = True
                qc = ch
                result.append(ch)
                i += 1
                continue

            if ch == '-' and i + 1 < len(sql) and sql[i + 1] == '-':
                in_line_comment = True
                result.append(ch)
                i += 1
                continue

            if ch == '/' and i + 1 < len(sql) and sql[i + 1] == '*':
                in_block_comment = True
                result.append(ch)
                i += 1
                continue

            # 检查函数名( 模式
            for fname, placeholder in func_map.items():
                flen = len(fname)
                if (i + flen + 1 <= len(sql)
                        and sql[i:i + flen].upper() == fname
                        and sql[i + flen] == '('
                        and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == '_'))):
                    result.append(placeholder + '(')
                    found.add(fname)
                    i += flen + 1
                    break
            else:
                result.append(ch)
                i += 1

        return ''.join(result), found

    @staticmethod
    def _unescape_functions(sql: str) -> str:
        """恢复被转义的函数名（使用 _FUNC_MAP 的反向映射）"""
        for placeholder, name in {v: k for k, v in SQLFormatterV5._FUNC_MAP.items()}.items():
            sql = sql.replace(placeholder, name)
        return sql

    @staticmethod
    def _restore_negation_syntax(text: str) -> str:
        """恢复被 sqlglot 重写的否定模式。

        sqlglot 将以下写法统一提取 NOT 到前面：
        - a IS NOT NULL      → NOT a IS NULL
        - a NOT LIKE 'x'     → NOT a LIKE 'x'
        - a NOT IN (...)     → NOT a IN (...)
        - a NOT BETWEEN x AND y → NOT a BETWEEN x AND y

        本方法将其恢复为更自然的写法。仅处理简单标识符（含表前缀）。
        """
        ident = r'\w+(?:\.\w+)*'
        # NOT identifier IS NULL → identifier IS NOT NULL
        text = re.sub(
            rf'\bNOT\s+({ident})\s+IS\s+NULL\b',
            r'\1 IS NOT NULL',
            text
        )
        # NOT identifier LIKE → identifier NOT LIKE
        text = re.sub(
            rf'\bNOT\s+({ident})\s+LIKE\b',
            r'\1 NOT LIKE',
            text
        )
        # NOT identifier IN ( → identifier NOT IN (
        text = re.sub(
            rf'\bNOT\s+({ident})\s+IN\s*\(',
            r'\1 NOT IN (',
            text
        )
        # NOT identifier BETWEEN → identifier NOT BETWEEN
        text = re.sub(
            rf'\bNOT\s+({ident})\s+BETWEEN\b',
            r'\1 NOT BETWEEN',
            text
        )
        return text

    @staticmethod
    def _restore_operator_syntax(text: str, original: str) -> str:
        """恢复被 sqlglot 重写的运算符和字面量。

        仅在原始 SQL 使用了非标准写法时才恢复：
        - <> → != (如果原始使用了 !=)
        - CAST('...' AS DATE) → DATE '...' (如果原始使用了 DATE 字面量)
        """
        # <> → != (仅当原始 SQL 使用了 !=)
        if '!=' in original and '<>' not in original.upper():
            text = text.replace('<>', '!=')

        # CAST('...' AS DATE) → DATE '...'
        if re.search(r'\bDATE\s+\'', original, re.IGNORECASE):
            text = re.sub(
                r"CAST\s*\(\s*'([^']+)'\s+AS\s+DATE\s*\)",
                r"DATE '\1'",
                text,
                flags=re.IGNORECASE
            )

        # RLIKE → REGEXP (如果原始使用了 regexp)
        if re.search(r'\bregexp\b', original, re.IGNORECASE):
            text = re.sub(r'\bRLIKE\b', 'REGEXP', text, flags=re.IGNORECASE)

        return text

    def _protect_backslash_strings(self, sql: str) -> tuple:
        """保护含反斜杠的字符串字面量，防止 sqlglot 重复转义。

        将 '\\\.' 这类含反斜杠的字符串替换为安全的占位符字符串，
        sqlglot 不会对普通字符串字面量做二次转义。

        Returns:
            (protected_sql, string_map) — string_map: {placeholder: original_content}
        """
        string_map = {}
        result = []
        i = 0
        in_str = False
        qc = None
        current = []
        counter = 0
        in_line_comment = False
        in_block_comment = False

        while i < len(sql):
            ch = sql[i]

            if in_line_comment:
                result.append(ch)
                if ch == '\n':
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                result.append(ch)
                if ch == '*' and i + 1 < len(sql) and sql[i + 1] == '/':
                    in_block_comment = False
                i += 1
                continue

            if in_str:
                current.append(ch)
                if ch == '\\' and i + 1 < len(sql):
                    current.append(sql[i + 1])
                    i += 2
                    continue
                if ch == qc:
                    content = ''.join(current)
                    inner = content[1:-1]  # 去掉首尾引号
                    if '\\' in inner:
                        placeholder = f'___BSTR{counter}___'
                        string_map[placeholder] = inner
                        result.append(qc + placeholder + qc)
                        counter += 1
                    else:
                        result.append(content)
                    in_str = False
                    current = []
                i += 1
                continue

            if ch in ("'", '"'):
                in_str = True
                qc = ch
                current = [ch]
                i += 1
                continue

            if ch == '-' and i + 1 < len(sql) and sql[i + 1] == '-':
                in_line_comment = True
                result.append(ch)
                i += 1
                continue

            if ch == '/' and i + 1 < len(sql) and sql[i + 1] == '*':
                in_block_comment = True
                result.append(ch)
                i += 1
                continue

            result.append(ch)
            i += 1

        return ''.join(result), string_map

    @staticmethod
    def _restore_backslash_strings(sql: str, string_map: dict) -> str:
        """恢复被保护的反斜杠字符串"""
        for placeholder, original in string_map.items():
            sql = sql.replace(placeholder, original)
        return sql

    def _protect_multi_line_blocks(self, sql: str) -> tuple:
        """保护多行函数调用块，防止 sqlglot 重组参数结构。

        检测跨 5 行以上的 CONCAT/SPLIT 调用，替换为占位符。
        这些块通常已经被用户手动排版对齐，不需要 sqlglot 重新格式化。

        Returns:
            (protected_sql, block_map) — block_map: {placeholder: original_block}
        """
        block_map = {}
        blocks = []

        for match in re.finditer(r'\b(CONCAT|SPLIT)\s*\(', sql, re.IGNORECASE):
            paren_start = match.end() - 1
            paren_end = self._find_matching_paren_str(sql, paren_start)
            if paren_end == -1:
                continue

            full_block = sql[match.start():paren_end + 1]
            if full_block.count('\n') >= 5:
                blocks.append((match.start(), paren_end + 1))

        # 去掉被其他块包含的嵌套块，只保留最外层
        filtered = []
        for start, end in blocks:
            contained = any(
                s2 <= start and end <= e2 and (s2, e2) != (start, end)
                for s2, e2 in blocks
            )
            if not contained:
                filtered.append((start, end))

        # 从后往前替换，避免位置偏移
        counter = 0
        for start, end in reversed(filtered):
            placeholder = f'___COMPLEX_{counter}___'
            block_map[placeholder] = sql[start:end]
            sql = sql[:start] + placeholder + sql[end:]
            counter += 1

        return sql, block_map

    @staticmethod
    def _restore_complex_blocks(sql: str, block_map: dict) -> str:
        """恢复被保护的多行块，保留原始排版"""
        for placeholder, original in block_map.items():
            sql = sql.replace(placeholder, original)
        return sql

    @staticmethod
    def _protect_comment_slash_star(sql: str) -> tuple:
        """保护 -- 注释内的 /* 和 */ 文本，防止 sqlglot 误解析。

        将 -- 注释内的 /* 替换为 ___CSS___ ，*/ 替换为 ___CSE___。
        跳过字符串和块注释内的内容。
        """
        result = []
        protect_map = {}
        counter = 0
        i = 0
        in_str = False
        qc = None
        in_block_comment = False

        while i < len(sql):
            ch = sql[i]

            if in_block_comment:
                result.append(ch)
                if ch == '*' and i + 1 < len(sql) and sql[i + 1] == '/':
                    in_block_comment = False
                i += 1
                continue

            if in_str:
                result.append(ch)
                if ch == '\\' and i + 1 < len(sql):
                    result.append(sql[i + 1])
                    i += 2
                    continue
                if ch == qc:
                    in_str = False
                i += 1
                continue

            if ch in ("'", '"'):
                in_str = True
                qc = ch
                result.append(ch)
                i += 1
                continue

            if ch == '/' and i + 1 < len(sql) and sql[i + 1] == '*':
                in_block_comment = True
                result.append(ch)
                i += 1
                continue

            # 检测 -- 行注释
            if ch == '-' and i + 1 < len(sql) and sql[i + 1] == '-':
                # 输出 --
                result.append(ch)
                i += 1
                result.append(ch)
                i += 1
                # 处理注释内容直到行尾
                while i < len(sql) and sql[i] not in ('\n', '\r'):
                    c2 = sql[i]
                    if c2 == '/' and i + 1 < len(sql) and sql[i + 1] == '*':
                        ph = f'___CSS{counter}___'
                        protect_map[ph] = '/*'
                        result.append(ph)
                        counter += 1
                        i += 2
                    elif c2 == '*' and i + 1 < len(sql) and sql[i + 1] == '/':
                        ph = f'___CSS{counter}___'
                        protect_map[ph] = '*/'
                        result.append(ph)
                        counter += 1
                        i += 2
                    else:
                        result.append(c2)
                        i += 1
                continue

            result.append(ch)
            i += 1

        return ''.join(result), protect_map

    @staticmethod
    def _restore_comment_slash_star(sql: str, protect_map: dict) -> str:
        """恢复被保护的 /* 和 */ 文本"""
        for placeholder, original in protect_map.items():
            sql = sql.replace(placeholder, original)
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
        all_in_comment_maps = []  # 收集所有语句的 IN 注释映射
        all_standalone_maps = {}  # 收集所有语句的独立注释占位符映射
        global_standalone_counter = 0  # 跨语句全局计数器，避免占位符名冲突

        for i, stmt in enumerate(statements):
            try:
                # 预处理：将 IN 子句中 'value'--comment 转为 /* comment */
                stmt, in_comment_map = self._preprocess_in_clause_comments(stmt)
                if in_comment_map:
                    all_in_comment_maps.append(in_comment_map)

                # 预处理：将被注释掉的SQL代码行转为占位符附在THEN值后
                stmt, standalone_map, global_standalone_counter = self._preserve_standalone_comments(
                    stmt, start_counter=global_standalone_counter)
                if standalone_map:
                    all_standalone_maps.update(standalone_map)

                # 预处理：提取 PARTITIONED BY 原始定义（sqlglot 会合并到主列并丢失类型）
                escaped_stmt, partition_info = self._extract_partitioned_by(stmt)

                # 转义 $ 符号（在 PARTITIONED BY 提取结果基础上继续）
                escaped_stmt, _ = self._escape_dollar_signs(escaped_stmt)

                # 预处理：保留函数名（sqlglot 会重写 NVL→COALESCE, SUBSTR→SUBSTRING, GET_JSON_OBJECT→路径重写）
                escaped_stmt, escaped_funcs = self._escape_functions(escaped_stmt)

                # 预处理：保护多行函数块（CONCAT/SPLIT 跨 5+ 行），防止 sqlglot 重组参数结构
                escaped_stmt, block_map = self._protect_multi_line_blocks(escaped_stmt)

                # 预处理：保护含反斜杠的字符串字面量，防止 sqlglot 重复转义
                escaped_stmt, bstr_map = self._protect_backslash_strings(escaped_stmt)

                # 预处理：保护 -- 注释内的 /* */ 文本
                escaped_stmt, comment_protect_map = self._protect_comment_slash_star(escaped_stmt)

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
                    # 恢复被保护的反斜杠字符串（必须在 _unescape_dollar_signs 之前，
                    # 因为被保护的字符串内容中可能包含 ___DOLLAR___ 占位符）
                    fmt = self._restore_backslash_strings(fmt, bstr_map)
                    # 恢复 $ 符号（在反斜杠字符串恢复之后，这样字符串中的 ___DOLLAR___ 也能被还原）
                    fmt = self._unescape_dollar_signs(fmt)
                    # 恢复被转义的函数名（NVL, SUBSTR, GET_JSON_OBJECT 等）
                    fmt = self._unescape_functions(fmt)
                    # 恢复注释内的 /* */ 文本
                    fmt = self._restore_comment_slash_star(fmt, comment_protect_map)
                    # 将 /* */ 改回 -- 格式
                    fmt = self._convert_block_comments_to_line_comments(fmt)
                    # V4 风格后处理（leading comma, AND/OR对齐, CASE WHEN等）
                    fmt = self._apply_v4_full_style(fmt)
                    # 恢复被 sqlglot 重写的否定语法（IS NOT NULL, NOT LIKE, NOT IN, NOT BETWEEN）
                    fmt = self._restore_negation_syntax(fmt)
                    # 恢复被 sqlglot 重写的运算符（!=, DATE字面量, regexp）
                    fmt = self._restore_operator_syntax(fmt, stmt)
                    # 修复子查询括号对齐和内容缩进
                    fmt = self._fix_subquery_indent(fmt)
                    # CREATE TABLE 列对齐（列名、类型、COMMENT上下对齐）
                    fmt = self._align_create_table_columns(fmt)
                    # 恢复 PARTITIONED BY 原始定义
                    fmt = self._restore_partitioned_by(fmt, partition_info)
                    # 拆分超长标量子查询
                    fmt = self._split_long_scalar_subqueries(fmt)
                    # 恢复被保护的多行函数块（CONCAT/SPLIT 等），保留原始排版
                    # 必须在所有其他后处理之后，避免缩进修复等步骤破坏块内换行
                    if block_map:
                        fmt = self._restore_complex_blocks(fmt, block_map)
                    # 分号独立行：避免追加到 -- 注释行末尾导致 ; 被注释吃掉
                    if not fmt.endswith(';'):
                        fmt += '\n;'
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
        result = '\n\n'.join(formatted_statements)

        # Step 5: 拆分被sqlglot合并的注释行
        result = self._split_merged_comment_lines(result)

        # Step 6: 拆分 IN 子句中被合并的注释值，同时恢复占位符为原始注释
        all_in_map = {}
        for m in all_in_comment_maps:
            all_in_map.update(m)
        result = self._split_in_clause_comments(result, all_in_map)

        # Step 7: 恢复独立注释占位符为原始注释行
        if all_standalone_maps:
            result = self._restore_standalone_placeholders(result, all_standalone_maps)

        return result


def format_sql_v5(sql: str, **options) -> str:
    """v5 格式化入口函数"""
    formatter = SQLFormatterV5(
        indent_spaces=options.get('indent', 4)
    )
    return formatter.format(sql)

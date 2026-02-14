"""
SQL 格式化器 - 智能缩进，支持多种嵌套场景
使用 sqlglot 进行解析，然后自定义格式化
"""
import re
import sqlglot
from sqlglot import exp
from sqlglot.dialects import Spark


class SQLFormatter:
    """SQL格式化器"""

    KEYWORDS_UPPER = {
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION', 'UNION ALL',
        'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'INNER JOIN', 'CROSS JOIN',
        'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL',
        'AS', 'DISTINCT', 'ALL', 'ANY', 'SOME',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'ON', 'INTO', 'VALUES', 'SET', 'BY', 'ASC', 'DESC', 'WITH', 'OVER', 'PARTITION', 'DISTRIBUTE'
    }

    def __init__(self, indent_spaces: int = 2):
        self.indent_spaces = indent_spaces

    def format(self, sql: str, **options) -> str:
        """格式化SQL语句"""
        try:
            keyword_case = options.get('keyword_case', 'upper')
            indent = options.get('indent', self.indent_spaces)
            semicolon = options.get('semicolon', True)

            cleaned = self._preprocess_sql(sql)
            formatted = self._format_sql(cleaned)

            if keyword_case == 'upper':
                formatted = self._uppercase_keywords(formatted)

            if semicolon and not formatted.rstrip().endswith(';'):
                formatted = formatted.rstrip() + '\n;'

            # 去除中间的无意义空行，但保留整段前后的空行
            formatted = self._remove_middle_blank_lines(formatted)

            return formatted

        except Exception as e:
            print(f"格式化失败: {e}")
            import traceback
            traceback.print_exc()
            return sql

    def _preprocess_sql(self, sql: str) -> str:
        """预处理SQL：保留注释"""
        lines = []
        for line in sql.split('\n'):
            # 保留整行内容，包括注释
            # 只去掉行尾空白，保留行首缩进和注释
            cleaned_line = line.rstrip()
            if cleaned_line:  # 保留非空行（包括注释行）
                lines.append(cleaned_line)
        return ' '.join(lines)

    def _format_sql(self, sql: str) -> str:
        """主格式化方法 - 支持嵌套子查询"""
        # 按顶级关键字分割（不在括号内的）
        major_kws = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'DISTRIBUTE BY', 'LIMIT', 'UNION', 'UNION ALL']
        # 按长度排序，优先匹配长的关键字
        major_kws_sorted = sorted(major_kws, key=len, reverse=True)

        parts = []
        last_pos = 0
        depth = 0
        in_string = False
        str_char = None
        i = 0

        while i < len(sql):
            char = sql[i]

            # 处理字符串
            if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
                i += 1
                continue

            if in_string:
                i += 1
                continue

            # 处理括号
            if char == '(':
                depth += 1
                i += 1
            elif char == ')':
                depth -= 1
                i += 1
            elif depth == 0:
                # 只在顶级查找关键字
                found_kw = None
                found_pos = -1
                for kw in major_kws_sorted:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    match = re.match(pattern, sql[i:], re.IGNORECASE)
                    if match:
                        found_kw = kw
                        found_pos = i
                        break

                if found_kw:
                    # 添加之前的内容
                    if found_pos > last_pos:
                        content = sql[last_pos:found_pos].strip()
                        if content:
                            parts.append(('CONTENT', content))
                    parts.append(('KEYWORD', found_kw.upper()))
                    last_pos = found_pos + len(found_kw)
                    i = last_pos
                    # 跳过关键字后的空格
                    while i < len(sql) and sql[i] in ' \t':
                        i += 1
                    last_pos = i
                else:
                    i += 1
            else:
                i += 1

        # 添加剩余内容
        if last_pos < len(sql):
            content = sql[last_pos:].strip()
            if content:
                parts.append(('CONTENT', content))

        # 处理每个部分
        lines = []
        base_indent = '  '

        for part_type, part_value in parts:
            if part_type == 'KEYWORD':
                if part_value == 'SELECT':
                    lines.append('SELECT')
                elif part_value == 'FROM':
                    lines.append('\nFROM')
                elif part_value in ('WHERE', 'GROUP BY', 'HAVING', 'DISTRIBUTE BY'):
                    lines.append('\n' + part_value)
                else:
                    lines.append('\n' + part_value)
            else:
                # 处理内容部分
                if not part_value:
                    continue
                # 判断当前是在哪个子句
                if lines and lines[-1].strip() == 'SELECT':
                    # SELECT子句 - 格式化字段列表
                    field_lines = self._format_select_fields(part_value)
                    lines.extend(field_lines)
                elif lines and lines[-1].strip() == 'FROM':
                    # FROM子句 - 处理表和JOIN
                    from_lines = self._format_from_clause(part_value)
                    lines.extend(from_lines)
                elif lines and lines[-1].strip() in ('WHERE', 'HAVING'):
                    # WHERE/HAVING子句 - 格式化条件
                    cond_lines = self._format_where_conditions(part_value)
                    lines.extend(cond_lines)
                else:
                    lines.append(' ' + part_value)

        return '\n'.join(lines)

    def _format_select_fields(self, content: str) -> list:
        """格式化SELECT字段列表"""
        fields = self._split_by_comma(content)
        lines = []
        base_indent = '  '

        for i, field in enumerate(fields):
            field = field.strip()
            if not field:
                continue

            # 检查是否包含CASE
            if re.search(r'\bCASE\b', field, re.IGNORECASE):
                case_lines = self._format_case_field(field, i > 0)
                lines.extend(case_lines)
            else:
                prefix = '' if i == 0 else ','
                lines.append(base_indent + prefix + ' ' + field)

        return lines

    def _format_from_clause(self, content: str) -> list:
        """格式化FROM子句，处理表和JOIN"""
        lines = []
        base_indent = '  '

        # JOIN 关键字模式（需要先匹配长的关键字）
        join_patterns = [
            'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN',
            'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN',
            'INNER JOIN', 'CROSS JOIN', 'JOIN'
        ]

        # 构建匹配模式
        all_patterns = join_patterns
        pattern = r'\b(' + '|'.join(all_patterns) + r')\b'

        # 分割内容
        parts = []
        last_pos = 0
        for m in re.finditer(pattern, content, re.IGNORECASE):
            if m.start() > last_pos:
                parts.append(('CONTENT', content[last_pos:m.start()].strip()))
            parts.append(('JOIN', m.group(1).upper()))
            last_pos = m.end()
        if last_pos < len(content):
            parts.append(('CONTENT', content[last_pos:].strip()))

        # 处理每个部分
        for part_type, part_value in parts:
            if part_type == 'JOIN':
                # JOIN 关键字换行
                lines.append('\n' + base_indent + part_value)
            else:
                # 内容部分 - 检查是否包含子查询，如果是则递归格式化
                if part_value:
                    # 检查是否包含子查询 (SELECT ... FROM ...)
                    if re.search(r'\bSELECT\b', part_value, re.IGNORECASE):
                        # 查找子查询的起始和结束位置
                        subquery_content = self._extract_and_format_subquery(part_value)
                        lines.append(' ' + subquery_content)
                    else:
                        lines.append(' ' + part_value)

        return lines

    def _extract_and_format_subquery(self, content: str) -> str:
        """提取并格式化子查询（处理 (SELECT...) alias [ON ...] 格式）"""
        content = content.strip()

        # 检查是否是 (SELECT ... ) alias 格式
        if content.startswith('('):
            # 找到匹配的最外层右括号位置
            depth = 0
            in_string = False
            str_char = None
            match_pos = -1

            for i, char in enumerate(content):
                if char in ("'", '"') and (i == 0 or content[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        str_char = char
                    elif char == str_char:
                        in_string = False
                elif in_string:
                    continue
                elif char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        match_pos = i
                        break

            if match_pos >= 0:
                # 提取子查询部分
                subquery_with_outer_parens = content[:match_pos+1]
                rest = content[match_pos+1:].strip()

                # 去掉子查询的外层括号
                subquery_inner = subquery_with_outer_parens[1:-1].strip()

                # 检查是否以 SELECT 开头
                if subquery_inner.upper().startswith('SELECT'):
                    # 格式化子查询
                    formatted_subquery = self._format_sql(subquery_inner)

                    # 处理别名和ON子句
                    # rest可能是 "t8 ON ..." 或只有 "t8"
                    # 找到ON关键字的位置（如果有）
                    on_match = re.search(r'\bON\b', rest, re.IGNORECASE)
                    if on_match:
                        alias_part = rest[:on_match.start()].strip()
                        on_clause = rest[on_match.start():].strip()
                        # 去除ON子句中函数调用参数里的多余括号（如 CAST((arg)) -> CAST(arg)）
                        on_clause = self._clean_function_calls(on_clause)
                        # 重新构造：缩进，括号，格式化的子查询，别名，换行，ON子句
                        return '\n(\n' + formatted_subquery + '\n) ' + alias_part + '\n  ' + on_clause
                    else:
                        # 没有ON子句，直接返回
                        return '(' + formatted_subquery + ') ' + rest

        return content

    def _clean_function_calls(self, text: str) -> str:
        """清理文本中函数调用参数里的多余括号，如 CAST((arg)) -> CAST(arg)"""
        # 使用正则表达式查找所有函数调用模式：FUNCTION_NAME(...)
        # 处理嵌套，但递归清理函数参数
        result = text
        # 查找函数名后面跟括号的模式
        func_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\(')

        def replace_func_call(match):
            func_name = match.group(1)
            func_start = match.start()
            # 从函数名后找到匹配的右括号
            depth = 0
            func_end = -1
            for i in range(func_start + len(func_name), len(result)):
                if result[i] == '(':
                    depth += 1
                elif result[i] == ')':
                    depth -= 1
                    if depth == 0:
                        func_end = i
                        break
            if func_end > 0:
                # 提取函数参数（去掉最外层括号）
                args = result[func_start + len(func_name) + 1:func_end]
                # 递归清理参数中的函数调用
                cleaned_args = self._clean_function_calls(args)
                # 去除参数外层的多余括号
                cleaned_args = self._remove_wrapping_parens(cleaned_args)
                # 重建函数调用
                return f'{func_name}({cleaned_args}){result[func_end + 1:]}'
            return match.group(0)

        # 从左到右处理所有函数调用
        i = 0
        while i < len(result):
            match = func_pattern.search(result[i:])
            if not match:
                break
            # 计算在原字符串中的位置
            abs_pos = i + match.start()
            func_name = match.group(1)
            # 找到匹配的右括号
            depth = 0
            func_end = -1
            for j in range(abs_pos + len(func_name), len(result)):
                if result[j] == '(':
                    depth += 1
                elif result[j] == ')':
                    depth -= 1
                    if depth == 0:
                        func_end = j
                        break
            if func_end > 0:
                # 提取参数并清理
                args = result[abs_pos + len(func_name) + 1:func_end]
                cleaned_args = self._clean_function_calls(args)
                cleaned_args = self._remove_wrapping_parens(cleaned_args)
                # 重建
                result = result[:abs_pos] + f'{func_name}({cleaned_args})' + result[func_end + 1:]
                i = abs_pos + len(f'{func_name}({cleaned_args})')
            else:
                i += 1

        return result

    def _format_case_field(self, field: str, has_comma: bool) -> list:
        """格式化CASE字段"""
        lines = []
        field = field.strip()

        # 移除前导逗号
        if field.startswith(','):
            field = field[1:].strip()

        base_indent = '  '
        when_indent = '    '
        or_indent = '       '

        prefix = ',' if has_comma else ''
        lines.append(base_indent + prefix + ' CASE')

        # 解析并格式化CASE
        result = self._parse_and_format_case(field)
        lines.extend(result)

        return lines

    def _parse_and_format_case(self, text: str) -> list:
        """解析并格式化CASE语句"""
        lines = []
        text = text.strip()

        # 移除开头的CASE
        if text.upper().startswith('CASE'):
            text = text[4:].strip()

        base_indent = '  '
        when_indent = '    '
        nested_indent = '      '

        i = 0
        while i < len(text):
            # 查找WHEN
            when_match = re.match(r'\bWHEN\b', text[i:], re.IGNORECASE)
            if when_match:
                i += 4
                cond_start = i
                # 查找THEN
                then_pos = self._find_keyword_outside_parens(text, i, 'THEN')
                if then_pos < 0:
                    break

                when_cond = text[i:then_pos].strip()
                i = then_pos + 4

                # 查找THEN值结束位置
                val_end = self._find_case_value_end(text, i)

                if val_end < 0:
                    break

                then_val = text[i:val_end].strip()
                i = val_end

                # 格式化WHEN条件（处理OR）
                if re.search(r'\bOR\b', when_cond, re.IGNORECASE):
                    or_parts = self._split_or_respecting_parens(when_cond)
                    lines.append(when_indent + 'WHEN ' + or_parts[0])
                    for part in or_parts[1:]:
                        lines.append(when_indent + '     OR ' + part)
                else:
                    lines.append(when_indent + 'WHEN ' + when_cond)

                # 格式化THEN值 - 保留原始结构，包括括号
                if then_val:
                    # 检查是否包含嵌套CASE
                    if re.search(r'\bCASE\b', then_val, re.IGNORECASE):
                        # 嵌套CASE - 保留完整结构，包括括号
                        # 直接输出原始内容，不做递归格式化（避免破坏嵌套结构）
                        lines.append(when_indent + 'THEN ' + then_val)
                    else:
                        # 普通值
                        lines.append(when_indent + 'THEN ' + then_val)
                continue

            # 查找ELSE
            else_match = re.match(r'\bELSE\b', text[i:], re.IGNORECASE)
            if else_match:
                i += 4
                else_start = i
                else_end = self._find_keyword_outside_parens(text, i, 'END')
                if else_end < 0:
                    break
                else_val = text[i:else_end].strip()
                i = else_end

                # 检查是否包含嵌套CASE - 保留完整结构，包括括号
                if re.search(r'\bCASE\b', else_val, re.IGNORECASE):
                    lines.append(when_indent + 'ELSE ' + else_val)
                else:
                    lines.append(when_indent + 'ELSE ' + else_val)
                continue

            # 查找END
            end_match = re.match(r'\bEND\b', text[i:], re.IGNORECASE)
            if end_match:
                i += 3
                # 获取别名
                while i < len(text) and text[i] in ' \t':
                    i += 1
                alias_start = i
                while i < len(text) and text[i] not in '\n;':
                    i += 1
                alias = text[alias_start:i].strip()
                lines.append(base_indent + 'END' + (' ' + alias if alias else ''))
                break

            i += 1

        return lines

    def _find_keyword_outside_parens(self, text: str, start: int, keyword: str) -> int:
        """在括号外查找关键字"""
        depth = 0
        in_string = False
        str_char = None
        i = start

        while i < len(text):
            char = text[i]

            if char in ("'", '"') and (i == 0 or text[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
                i += 1
                continue

            if in_string:
                i += 1
                continue

            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif depth == 0 and re.match(r'\b' + keyword + r'\b', text[i:], re.IGNORECASE):
                return i

            i += 1

        return -1

    def _find_case_value_end(self, text: str, start: int) -> int:
        """查找CASE值的结束位置（下一个WHEN/ELSE/END）"""
        depth = 0
        in_string = False
        str_char = None
        i = start

        while i < len(text):
            char = text[i]

            if char in ("'", '"') and (i == 0 or text[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
                i += 1
                continue

            if in_string:
                i += 1
                continue

            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif depth == 0:
                if re.match(r'\bWHEN\b', text[i:], re.IGNORECASE):
                    return i
                elif re.match(r'\bELSE\b', text[i:], re.IGNORECASE):
                    return i
                elif re.match(r'\bEND\b', text[i:], re.IGNORECASE):
                    return i

            i += 1

        return -1

    def _split_or_respecting_parens(self, condition: str) -> list:
        """分割OR条件，尊重括号和字符串"""
        parts = []
        current = ''
        depth = 0
        in_string = False
        str_char = None
        i = 0

        while i < len(condition):
            char = condition[i]

            if char in ("'", '"') and (i == 0 or condition[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
                current += char
                i += 1
                continue

            if in_string:
                current += char
                i += 1
                continue

            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif depth == 0 and re.match(r'\bOR\b', condition[i:], re.IGNORECASE):
                if current.strip():
                    parts.append(current.strip())
                current = ''
                i += 2  # 跳过OR
            else:
                current += char

            i += 1

        if current.strip():
            parts.append(current.strip())

        return parts

    def _format_where_conditions(self, content: str) -> list:
        """格式化WHERE条件，处理连续的OR/AND换行"""
        lines = []
        indent = '    '
        debug_mode = False  # Set to True for debug output

        # 先尝试去除外层括号（现在_remove_wrapping_parens已经能正确处理函数调用）
        content = self._remove_wrapping_parens(content)

        if debug_mode:
            print(f"DEBUG after _remove_wrapping_parens: {repr(content[:100])}")
            if '((' in content or '))' in content:
                print(f"  ^^^ STILL HAS DOUBLE PARENTHESES!")

        # 分割顶级AND/OR（不在括号内的）
        parts = self._split_and_or(content)

        if debug_mode:
            print(f"DEBUG after _split_and_or: {len(parts)} parts")
            for i, (op, part) in enumerate(parts):
                print(f"  Part {i} [{op}]: {repr(part[:50])}")

        if len(parts) <= 1:
            # 单个条件，检查是否包含需要展开的括号内OR/AND
            condition = content.strip()
            lines.extend(self._format_single_condition(condition, indent))
        else:
            for i, (operator, condition) in enumerate(parts):
                condition = condition.strip()
                if debug_mode and '((' in condition:
                    print(f"  Part {i} before _remove_wrapping_parens has (( : {repr(condition[:50])}")
                # 去掉多余的外层括号
                condition = self._remove_wrapping_parens(condition)

                if debug_mode and '((' in condition:
                    print(f"  Part {i} after _remove_wrapping_parens STILL has (( : {repr(condition[:50])}")

                # 格式化单个条件（可能包含括号内的OR/AND）
                condition_lines = self._format_single_condition(condition, indent)

                if i == 0:
                    # 第一个条件不需要前缀
                    lines.extend(condition_lines)
                else:
                    # 后续条件需要 AND/OR 前缀
                    if condition_lines:
                        first = condition_lines[0]
                        # 将前缀添加到第一行
                        lines.append('\n' + indent + operator.upper() + ' ' + first.lstrip())
                        # 添加剩余行（带缩进）
                        for line in condition_lines[1:]:
                            lines.append('\n' + indent + '    ' + line.lstrip())

        return lines

    def _format_single_condition(self, condition: str, indent: str) -> list:
        """格式化单个条件，展开OR/AND（无论是否有外层括号）"""
        condition = condition.strip()
        lines = []

        # 检查是否被外层括号包裹且包含OR/AND
        has_outer_parens = condition.startswith('(') and condition.endswith(')')
        inner_content = condition[1:-1].strip() if has_outer_parens else condition

        # 检查内容中是否有顶级OR/AND
        has_or = self._has_top_level_operator(inner_content, 'OR')
        has_and = self._has_top_level_operator(inner_content, 'AND')

        if has_or or has_and:
            # 有顶级OR/AND，去掉外层括号，展开每个条件为单独一行
            parts = self._split_and_or(inner_content)
            for i, (op, cond) in enumerate(parts):
                cond = cond.strip()
                cond = self._remove_wrapping_parens(cond)
                if cond:  # 只添加非空条件
                    if i == 0:
                        lines.append('\n' + indent + cond)
                    else:
                        lines.append('\n' + indent + op.upper() + ' ' + cond)
            return lines

        # 普通条件，直接输出
        lines.append('\n' + indent + condition)
        return lines

    def _has_top_level_operator(self, text: str, operator: str) -> bool:
        """检查文本是否有顶级的AND/OR（不在括号内的）"""
        parts = self._split_and_or(text)
        return len(parts) > 1 and any(op.upper() == operator.upper() for op, _ in parts)

    def _split_and_or(self, content: str) -> list:
        """分割AND/OR条件"""
        result = []
        current = ''
        depth = 0
        in_string = False
        str_char = None
        i = 0
        last_op = ''

        # Debug: Check if content already has double parentheses at start
        debug_mode = False  # Set to True to enable debug output
        trace_mode = False  # Trace every character

        # Always print input for debugging
        call_count = [0]  # Use list to make it mutable across calls
        if debug_mode:
            call_count[0] += 1
            print(f"DEBUG _split_and_or call #{call_count[0]}: input={repr(content[:80])}")
            if 'NVL' in content or 'CAST' in content:
                trace_mode = True  # Enable trace for NVL/CAST cases
                print(f"  Enabling trace for NVL/CAST")
            if '((' in content or '))' in content:
                print(f"  ^^^ INPUT HAS DOUBLE PARENTHESES!")
                if '((' in content[:30]:
                    trace_mode = True
                    print(f"  Input chars:")
                    for j, c in enumerate(content[:20]):
                        print(f"    pos {j}: {repr(c)} ord={ord(c)}")

        while i < len(content):
            char = content[i]

            if trace_mode:
                print(f"  pos {i}: char={repr(char)} ord={ord(char)} depth={depth} in_string={in_string} current=\"{current[-30:]}\"", end="")

                # Check if current has unexpected double parens
                if 'NVL' in current and current.count('(') > 1 and 't1.acc' in current:
                    print(f" UNEXPECTED! current has {(current.count('('))} opens: {repr(current[-30:])}", end="")
                elif 'CAST' in current and current.count('(') > 1 and 'corp_inn_accno' in current:
                    print(f" UNEXPECTED! current has {(current.count('('))} opens: {repr(current[-30:])}", end="")

            if char in ("'", '"') and (i == 0 or content[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
                current += char
                if trace_mode:
                    print(f" -> string toggle, current now: {repr(current[-20:])}")
                i += 1
                continue

            if in_string:
                current += char
                if trace_mode:
                    print(f" -> in string, current now: {repr(current[-20:])}")
                i += 1
                continue

            if char == '(':
                depth += 1
                if debug_mode and i < 20:
                    print(f"DEBUG pos {i}: '(', current now ends with: {repr(current[-20:])}")
            elif char == ')':
                depth -= 1
                if debug_mode and i < 20:
                    print(f"DEBUG pos {i}: ')', current now ends with: {repr(current[-20:])}")
            elif depth == 0:
                if re.match(r'\bAND\b', content[i:], re.IGNORECASE):
                    if current.strip():
                        result.append((last_op, current.strip()))
                    current = ''
                    i += 3
                    last_op = 'AND'
                    # 跳过空格
                    while i < len(content) and content[i] in ' \t':
                        i += 1
                    continue
                elif re.match(r'\bOR\b', content[i:], re.IGNORECASE):
                    if current.strip():
                        result.append((last_op, current.strip()))
                    current = ''
                    i += 2
                    last_op = 'OR'
                    while i < len(content) and content[i] in ' \t':
                        i += 1
                    continue

            current += char
            i += 1

        if current.strip():
            result.append((last_op, current.strip()))
            if debug_mode:
                print(f"DEBUG final current: {repr(current)}")

        if debug_mode:
            print(f"DEBUG result: {result}")
            # Check if result has double parentheses
            for i, (op, part) in enumerate(result):
                if '((' in part or '))' in part:
                    print(f"  ^^^ Part {i} [{op}] has double parentheses: {repr(part[:60])}")

        return result

    def _split_by_comma(self, content: str) -> list:
        """按逗号分割，尊重括号"""
        parts = []
        current = ''
        depth = 0
        in_string = False
        str_char = None

        for i, char in enumerate(content):
            if char in ("'", '"') and (i == 0 or content[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
                current += char
            elif in_string:
                current += char
            elif char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                if current.strip():
                    parts.append(current.strip())
                current = ''
            else:
                current += char

        if current.strip():
            parts.append(current.strip())
        return parts

    def _remove_wrapping_parens(self, text: str) -> str:
        """去掉包裹整个表达式的外层括号（如果存在），递归处理双重括号"""
        debug = False  # Set to True for debug
        if debug:
            print(f"  _remove_wrapping_parens input: {repr(text[:50])}")

        text = text.strip()

        # 首先检查是否是函数调用格式（不管是否以(开头）
        # 函数调用格式的特征：以函数名开头，后面跟左括号
        function_call_pattern = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]+)\(', text)

        if function_call_pattern:
            # 这是一个函数调用，检查参数部分是否有多余的括号
            func_name = function_call_pattern.group(1)
            if debug:
                print(f"  -> Function call detected: {func_name}")
            # 提取函数的参数部分（从第一个(到最后一个)）
            args_start = len(func_name)  # 第一个括号的位置
            # 找到匹配的最后一个括号
            depth = 0
            args_end = -1
            for i in range(args_start, len(text)):
                if text[i] == '(':
                    depth += 1
                elif text[i] == ')':
                    depth -= 1
                    if depth == 0:
                        args_end = i
                        break
            if args_end > 0:
                args = text[args_start + 1:args_end]  # 去掉外层的括号
                # 递归去除参数部分的包裹括号
                cleaned_args = self._remove_wrapping_parens(args)
                if debug:
                    print(f"  -> Original args: {repr(args[:40])}")
                    print(f"  -> Cleaned args: {repr(cleaned_args[:40])}")
                # 重新构建函数调用
                return f"{func_name}({cleaned_args}){text[args_end + 1:]}"
            # 如果找不到匹配的括号，返回原文本
            return text

        # 检查括号是否匹配（整个表达式被一对括号包裹）
        depth = 0
        in_string = False
        str_char = None
        first_close_after_zero = -1

        for i, char in enumerate(text):
            if char in ("'", '"') and (i == 0 or text[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
            elif in_string:
                continue
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0 and first_close_after_zero < 0:
                    first_close_after_zero = i
                if depth == 0 and i < len(text) - 1:
                    # 在结束前就匹配了，说明不是包裹整个表达式的括号
                    if debug:
                        print(f"  -> Not fully wrapped, return as-is")
                    return text

        # 如果最外层是匹配的括号，去掉它们，然后递归处理
        if depth == 0 and text.startswith('(') and text.endswith(')'):
            inner = text[1:-1].strip()
            if debug:
                print(f"  -> Removing outer parens, inner: {repr(inner[:50])}")
            # 检查去掉后是否是有效的表达式（不是函数名单独存在）
            if inner and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\([^)]*$', inner):
                # 递归去掉可能的双重括号
                result = self._remove_wrapping_parens(inner)
                if debug:
                    print(f"  -> Recursive result: {repr(result[:50])}")
                # 如果递归后内容相同，说明不能再去了，返回去掉一层括号的结果
                if result == inner:
                    if debug:
                        print(f"  -> Result == inner, returning inner")
                    return inner
                if debug:
                    print(f"  -> Returning recursive result")
                return result

        if debug:
            print(f"  -> Returning original text")
        return text

    def _uppercase_keywords(self, sql: str) -> str:
        """关键字大写"""
        for keyword in sorted(self.KEYWORDS_UPPER, key=len, reverse=True):
            pattern = r'\b' + re.escape(keyword) + r'\b'
            sql = re.sub(pattern, keyword, sql, flags=re.IGNORECASE)
        return sql

    def _remove_middle_blank_lines(self, sql: str) -> str:
        """去除中间的无意义空行，但保留整段前后的空行"""
        lines = sql.split('\n')

        # 找到第一个非空行和最后一个非空行
        first_non_empty = 0
        last_non_empty = len(lines) - 1

        while first_non_empty < len(lines) and not lines[first_non_empty].strip():
            first_non_empty += 1

        while last_non_empty >= 0 and not lines[last_non_empty].strip():
            last_non_empty -= 1

        # 如果全是空行，直接返回
        if first_non_empty >= len(lines):
            return sql

        # 处理中间部分：去除空行
        result = []

        # 保留开头的空行
        for i in range(first_non_empty):
            result.append(lines[i])

        # 中间部分去除空行
        for i in range(first_non_empty, last_non_empty + 1):
            if lines[i].strip():  # 只保留非空行
                result.append(lines[i])

        # 保留结尾的空行
        for i in range(last_non_empty + 1, len(lines)):
            result.append(lines[i])

        return '\n'.join(result)


_formatter = None

def format_sql(sql: str, **options) -> str:
    """格式化SQL语句"""
    global _formatter
    if _formatter is None:
        _formatter = SQLFormatter(indent_spaces=2)
    return _formatter.format(sql, **options)

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
        'AS', 'DISTINCT', 'ALL', 'ANY', 'SOME', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'ON', 'INTO', 'VALUES', 'SET', 'BY', 'ASC', 'DESC', 'WITH', 'OVER',
        'PARTITION', 'DISTRIBUTE', 'LATERAL', 'WINDOW', 'ROWS', 'RANGE',
        'UNBOUNDED', 'PRECEDING', 'FOLLOWING', 'EXPLAIN', 'FORMAT'
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
            cleaned_line = line.rstrip()
            if cleaned_line:
                lines.append(cleaned_line)
        return ' '.join(lines)

    def _format_sql(self, sql: str) -> str:
        """主格式化方法 - 支持嵌套子查询"""
        # 按主要关键字分割
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
            elif in_string:
                i += 1
                continue

            # 处理括号和关键字（在字符串外）
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif depth == 0:
                # 只在顶级（depth=0）查找关键字
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

                    # 添加关键字
                    parts.append(('KEYWORD', found_kw.upper()))
                    last_pos = found_pos + len(found_kw)
                    i = last_pos
                    # 跳过关键字后的空格
                    while i < len(sql) and sql[i] in ' \t':
                        i += 1
                    last_pos = i

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
                elif part_value in ('WHERE', 'HAVING', 'DISTRIBUTE BY'):
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

        # JOIN关键字模式（需要先匹配长的）
        join_patterns = [
            'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN',
            'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN',
            'INNER JOIN', 'CROSS JOIN', 'JOIN'
        ]

        # 构建匹配模式
        pattern = r'\b(' + '|'.join(join_patterns) + r')\b'

        # 分割内容
        parts = []
        last_pos = 0
        for m in re.finditer(pattern, content, re.IGNORECASE):
            if m.start() > last_pos:
                if m.start() > last_pos:
                    content = content[last_pos:m.start()].strip()
                    if content:
                        parts.append(('CONTENT', content))
                parts.append(('JOIN', m.group(1).upper()))
                last_pos = m.end()

        if last_pos < len(content):
            content = content[last_pos:].strip()
            if content:
                parts.append(('CONTENT', content))

        # 处理每个部分
        for part_type, part_value in parts:
            if part_type == 'JOIN':
                lines.append('\n' + base_indent + part_value)
            else:
                if part_value:
                    lines.append('\n' + base_indent + part_value)

        return lines

    def _format_where_conditions(self, content: str) -> list:
        """格式化WHERE条件，处理连续的OR/AND换行"""
        lines = []
        indent = '    '

        # 暂时跳过 _remove_wrapping_parens 以避免破坏函数调用
        # 检查是否包含函数调用模式（FUNCTION(...)），如果是则跳过去除外层括号处理
        has_function_call = re.search(r'[a-zA-Z_][a-zA-Z0-9_]+\(', content)
        if has_function_call:
            # 对于函数调用，保持原样，不进行除外层括号处理
            # 例如：NVL(t1.acc ,'') 或 CAST(t8.corp_inn_accno AS string)
            return self._format_where_conditions_simple(content)

        # 正常情况：先尝试去除外层括号
        content = self._remove_wrapping_parens(content)

        # 分割顶级AND/OR（不在括号内的）
        parts = self._split_and_or(content)

        if len(parts) <= 1:
            # 单个条件，格式化并添加
            condition = content.strip()
            lines.extend(self._format_single_condition(condition, indent))
        else:
            # 多个条件，每个条件单独一行
            for i, (operator, condition) in enumerate(parts):
                condition = condition.strip()
                condition = self._remove_wrapping_parens(condition)
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

    def _format_where_conditions_simple(self, content: str) -> list:
        """简单格式化WHERE条件（不处理AND/OR分割）"""
        lines = []
        indent = '    '

        # 对单个条件进行格式化
        lines.append('\n' + indent + content.strip())

        return lines

    def _format_single_condition(self, condition: str, indent: str) -> list:
        """格式化单个条件"""
        lines = []
        condition = condition.strip()

        # 展开 OR/AND 条件（无论是否有外层括号）
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
                if cond:
                    if i == 0:
                        lines.append('\n' + indent + cond)
                    else:
                        lines.append('\n' + indent + op.upper() + ' ' + cond)
            return lines
        else:
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

        while i < len(content):
            char = content[i]

            # 处理字符串
            if char in ("'", '"') and (i == 0 or content[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
            elif in_string:
                current += char
                i += 1
                continue

            # 处理括号和AND/OR关键字（在字符串外）
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif depth == 0:
                # 查找AND关键字
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
                # 查找OR关键字
                elif re.match(r'\bOR\b', content[i:], re.IGNORECASE):
                    if current.strip():
                        result.append((last_op, current.strip()))
                    current = ''
                    i += 2
                    last_op = 'OR'
                    while i < len(content) and content[i] in ' \t':
                        i += 1
                    continue

            # 其他字符
            current += char
            i += 1

        if current.strip():
            result.append((last_op, current.strip()))

        return result

    def _split_by_comma(self, content: str) -> list:
        """按逗号分割，尊重括号"""
        parts = []
        current = ''
        depth = 0
        in_string = False
        str_char = None

        for char in enumerate(content):
            if char in ("'", '"') and (char == 0 or content[char-1] != '\\'):
                if not in_string:
                    in_string = True
                    str_char = char
                elif char == str_char:
                    in_string = False
            elif in_string:
                current += char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                if current.strip():
                    parts.append(current.strip())
                current = ''
            else:
                current += char

        if current.strip():
            parts.append(current.strip())

        return parts

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

        # 中间部分：只保留非空行
        for i in range(first_non_empty, last_non_empty + 1):
            if lines[i].strip():
                result.append(lines[i])

        # 保留结尾的空行
        for i in range(last_non_empty + 1, len(lines)):
            result.append(lines[i])

        return '\n'.join(result)

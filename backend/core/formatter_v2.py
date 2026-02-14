# -*- coding: utf-8 -*-
"""
SQL 格式化器 - 符合开发规范版本
基于原有 formatter.py 优化，符合《大数据SQL开发规范》要求
"""
import re
import sqlglot
from sqlglot import exp
from sqlglot.dialects import Spark


class SQLFormatterV2:
    """
    SQL格式化器 V2 - 符合开发规范

    规范要求：
    1. 统一用4个空格缩进
    2. 逗号写在字段名前面，实现左对齐
    3. GROUP BY/ORDER BY 与 SELECT 左对齐
    4. WHERE 中 AND 与 WHERE 右对齐
    5. JOIN 中 ON 与 JOIN 右对齐
    6. 每行宽度不超过250字符
    7. 分号另起一行
    """

    # 需要大写的关键字
    KEYWORDS_UPPER = {
        'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION', 'UNION ALL',
        'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'INNER JOIN', 'CROSS JOIN',
        'LEFT SEMI JOIN', 'LEFT ANTI JOIN', 'RIGHT SEMI JOIN', 'RIGHT ANTI JOIN',
        'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL',
        'AS', 'DISTINCT', 'ALL', 'ANY', 'SOME',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'ON', 'INTO', 'VALUES', 'SET', 'BY', 'ASC', 'DESC', 'WITH', 'OVER', 'PARTITION', 'DISTRIBUTE'
    }

    def __init__(self, indent_spaces: int = 4, max_line_length: int = 250):
        """
        初始化格式化器

        Args:
            indent_spaces: 缩进空格数（规范要求4个空格）
            max_line_length: 最大行长度（规范要求不超过250字符）
        """
        self.indent_spaces = indent_spaces
        self.max_line_length = max_line_length

    def format(self, sql: str, **options) -> str:
        """
        格式化SQL语句

        Args:
            sql: 原始SQL语句
            **options: 格式化选项
                - keyword_case: 关键字大小写 (upper/lower，默认 upper)
                - semicolon_newline: 分号另起一行 (默认 True)

        Returns:
            格式化后的SQL字符串
        """
        try:
            keyword_case = options.get('keyword_case', 'upper')
            semicolon_newline = options.get('semicolon_newline', True)

            # 预处理
            cleaned = self._preprocess_sql(sql)

            # 格式化
            formatted = self._format_sql(cleaned)

            # 关键字大写
            if keyword_case == 'upper':
                formatted = self._uppercase_keywords(formatted)

            # 分号另起一行
            if semicolon_newline:
                formatted = formatted.rstrip(';').strip() + '\n;'

            # 去除中间空行
            formatted = self._remove_middle_blank_lines(formatted)

            # 检查行长度
            formatted = self._check_line_length(formatted)

            return formatted

        except Exception as e:
            print(f"格式化失败: {e}")
            import traceback
            traceback.print_exc()
            return sql

    def _preprocess_sql(self, sql: str) -> str:
        """预处理SQL：保留注释，去除多余空白"""
        lines = []
        for line in sql.split('\n'):
            cleaned_line = line.rstrip()
            if cleaned_line:
                lines.append(cleaned_line)
        return ' '.join(lines)

    def _format_sql(self, sql: str) -> str:
        """主格式化方法"""
        # 使用 sqlglot 解析
        try:
            parsed = sqlglot.parse_one(sql, dialect=Spark)
        except Exception as e:
            # 解析失败，使用简单格式化
            return self._simple_format(sql)

        if not isinstance(parsed, exp.Select):
            return self._simple_format(sql)

        parts = []
        indent = ' ' * self.indent_spaces

        # SELECT 子句
        if parsed.expressions:
            select_lines = self._format_select_fields(parsed)
            parts.append('\n'.join(select_lines))

        # FROM 子句
        if parsed.args.get('from'):
            from_lines = self._format_from_clause(parsed)
            # 确保第一个 FROM 前面有换行
            if from_lines and from_lines[0].startswith('\nFROM'):
                pass  # 已经有换行
            elif from_lines:
                from_lines[0] = '\n' + from_lines[0]
            else:
                from_lines = ['\nFROM ' + from_lines[0]]
            parts.extend(from_lines)

        # WHERE 子句
        if parsed.args.get('where'):
            where_lines = self._format_where_conditions(parsed.args['where'])
            # 确保第一个 WHERE 前面有换行
            if where_lines and not where_lines[0].startswith('\nWHERE'):
                where_lines[0] = '\n' + where_lines[0]
            parts.append('\n'.join(where_lines))

        # GROUP BY 子句
        if parsed.args.get('group'):
            group_lines = self._format_group_by(parsed)
            # 确保第一个 GROUP BY 前面有换行
            if group_lines and not group_lines[0].startswith('\nGROUP BY'):
                group_lines[0] = '\n' + group_lines[0]
            parts.append('\n'.join(group_lines))

        # HAVING 子句
        if parsed.args.get('having'):
            having_lines = self._format_having(parsed.args['having'])
            parts.append('\n'.join(having_lines))

        # ORDER BY 子句
        if parsed.args.get('order'):
            order_lines = self._format_order_by(parsed)
            # 确保第一个 ORDER BY 前面有换行
            if order_lines and not order_lines[0].startswith('\nORDER BY'):
                order_lines[0] = '\n' + order_lines[0]
            parts.append('\n'.join(order_lines))

        # LIMIT 子句
        if parsed.args.get('limit'):
            parts.append('\nLIMIT ' + parsed.args['limit'].sql())

        return '\n'.join(parts)

    def _simple_format(self, sql: str) -> str:
        """简单格式化（当sqlglot解析失败时使用）"""
        # 简单的关键字分行处理
        major_kws = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT']
        result = sql
        for kw in major_kws:
            result = re.sub(r'\b' + kw + r'\b', '\n' + kw, result, flags=re.IGNORECASE)
        return result

    def _format_select_fields(self, parsed: exp.Select) -> list:
        """
        格式化SELECT字段列表 - 逗号前置格式

        规范示例：
        SELECT t1.column1
             , t2.column2
             , NVL(t3.column3, '') AS column3
        """
        lines = []
        fields = parsed.expressions

        if not fields:
            return ['SELECT *']

        # 第一行：SELECT + 第一个字段
        first_field = self._format_field(fields[0])
        lines.append('SELECT ' + first_field)

        # 后续行：逗号前置
        # 计算缩进：与 SELECT 右对齐
        comma_indent = ' ' * len('SELECT')

        for field in fields[1:]:
            formatted_field = self._format_field(field)
            lines.append(f'{comma_indent}, {formatted_field}')

        return lines

    def _format_field(self, field: exp.Expression) -> str:
        """格式化单个字段表达式"""
        field_sql = field.sql()

        # 处理 CASE 表达式
        if isinstance(field, exp.Case):
            return self._format_case_expression(field)

        return field_sql

    def _format_case_expression(self, case_expr: exp.Case) -> str:
        """
        格式化CASE表达式

        规范要求：
        - CASE 与 END 对齐
        - WHEN 与 ELSE 对齐
        - 每个 WHEN 子句独立一行
        - OR 条件与 WHEN 右对齐

        示例：
        CASE WHEN t1.status = '1' AND t1.type = 'A' THEN '类型A'
             WHEN t1.status = '1' OR t1.type = 'B' THEN '类型B'
             WHEN t1.status = '2' THEN '其他'
             ELSE '未知'
        END AS status_desc
        """
        lines = []
        indent = ' ' * self.indent_spaces
        when_indent = ' ' * (self.indent_spaces * 2)  # WHEN 缩进

        # 获取 ifs (WHEN 条件)
        ifs = case_expr.args.get('ifs', [])
        default = case_expr.args.get('default')

        # 格式化每个 WHEN
        for i, if_expr in enumerate(ifs):
            condition = if_expr.this.sql()  # WHEN 条件
            then_value = if_expr.args['then'].sql()  # THEN 值

            # 检查条件中是否有 OR，如果有则展开
            if self._has_top_level_or(condition):
                # 分割 OR 条件
                or_parts = self._split_or_conditions(condition)
                # 第一个 OR 条件与 WHEN 在同一行
                lines.append(f'{when_indent}WHEN {or_parts[0]}')
                # 后续 OR 条件右对齐到 WHEN
                or_indent = ' ' * (len('WHEN') - len('OR'))
                for or_part in or_parts[1:]:
                    lines.append(f'{when_indent}{or_indent}OR {or_part}')
            else:
                lines.append(f'{when_indent}WHEN {condition}')

            # THEN 值（缩进更多以便与 WHEN 对齐）
            then_indent = ' ' * len('WHEN')
            lines.append(f'{when_indent}{then_indent}THEN {then_value}')

        # ELSE 子句
        if default:
            else_value = default.sql()
            else_indent = ' ' * len('WHEN')
            lines.append(f'{when_indent}{else_indent}ELSE {else_value}')

        # END
        lines.append(f'{indent}END')

        # 处理别名（如果有）
        alias = case_expr.args.get('alias')
        if alias:
            lines[-1] += ' ' + alias.sql()

        return '\n'.join(lines)

    def _has_top_level_or(self, condition: str) -> bool:
        """检查条件是否有顶级的OR（不在括号内的）"""
        depth = 0
        in_string = False
        str_char = None

        for i, char in enumerate(condition):
            if char in ("'", '"') and (i == 0 or condition[i-1] != '\\'):
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
            elif depth == 0 and re.match(r'\bOR\b', condition[i:], re.IGNORECASE):
                return True

        return False

    def _split_or_conditions(self, condition: str) -> list:
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
                i += 2
                while i < len(condition) and condition[i] in ' \t':
                    i += 1
            else:
                current += char

            i += 1

        if current.strip():
            parts.append(current.strip())

        return parts

    def _format_from_clause(self, parsed: exp.Select) -> list:
        """
        格式化FROM和JOIN子句

        规范要求：
        - JOIN 关键字换行
        - ON 与 JOIN 右对齐
        - 多个 ON 条件用 AND 连接，AND 与 ON 对齐

        示例：
        FROM table1 t1
        LEFT JOIN table2 t2
                   ON t1.id = t2.id
                  AND t2.status = '1'
        """
        lines = []
        from_expr = parsed.args.get('from')

        if not from_expr:
            return []

        indent = ' ' * self.indent_spaces

        # 主表
        main_table = from_expr.this.sql()
        lines.append(f'\nFROM {main_table}')

        # JOIN 子句
        joins = parsed.args.get('joins', [])

        for join in joins:
            join_kind = join.args.get('kind', '').upper()
            join_side = join.args.get('side', '').upper()

            # 构建完整的 JOIN 关键字（如 LEFT JOIN, LEFT SEMI JOIN）
            join_parts = []
            if join_side:
                join_parts.append(join_side)
            if join_kind:
                join_parts.append(join_kind)
            join_parts.append('JOIN')
            join_keyword = ' '.join(join_parts).strip()

            # 表名
            table = join.this.sql()
            lines.append(f'{indent}{join_keyword} {table}')

            # ON 条件
            on_expr = join.args.get('on')
            if on_expr:
                on_sql = self._format_on_conditions(on_expr, join_keyword)
                lines.append(on_sql)

        return lines

    def _format_on_conditions(self, on_expr: exp.Expression, join_keyword: str) -> str:
        """
        格式化ON条件

        规范要求：
        - ON 与 JOIN 右对齐
        - 多个条件用 AND 连接，AND 与 ON 对齐
        """
        indent = ' ' * self.indent_spaces

        # 检查是否是 AND 连接的多个条件
        conditions = self._extract_and_conditions(on_expr)

        if not conditions:
            return ''

        # 计算缩进：ON 右对齐到 JOIN
        on_indent = ' ' * (len(join_keyword) - len('ON'))

        # 第一个条件
        first_cond = conditions[0].sql()
        result = f'{indent}{on_indent}ON {first_cond}'

        # 后续条件（AND 连接）
        and_indent = ' ' * (len(join_keyword) - len('AND'))
        for cond in conditions[1:]:
            cond_sql = cond.sql()
            result += f'\n{indent}{and_indent}AND {cond_sql}'

        return result

    def _extract_and_conditions(self, expr: exp.Expression) -> list:
        """提取AND连接的条件列表"""
        if isinstance(expr, exp.And):
            left = self._extract_and_conditions(expr.left)
            right = self._extract_and_conditions(expr.right)
            return left + right
        return [expr]

    def _format_where_conditions(self, where_expr: exp.Expression) -> list:
        """
        格式化WHERE条件

        规范要求：
        - AND 与 WHERE 右对齐
        - OR 条件展开，每个条件独立一行
        - OR 与 WHERE 对齐

        示例：
        WHERE t1.status = '1'
          AND t2.date_col >= '2024-01-01'
          AND t3.amount > 0
        """
        lines = []
        indent = ' ' * self.indent_spaces

        # 提取顶级条件（AND连接）
        conditions = self._extract_and_conditions(where_expr)

        if not conditions:
            return []

        # 第一个条件
        first_cond = self._format_single_condition(conditions[0])
        lines.append(f'\nWHERE {first_cond}')

        # 后续条件
        and_indent = ' ' * (len('WHERE') - len('AND'))
        for cond in conditions[1:]:
            formatted_cond = self._format_single_condition(cond)
            lines.append(f'{indent}{and_indent}AND {formatted_cond}')

        return lines

    def _format_single_condition(self, cond: exp.Expression) -> str:
        """格式化单个条件，处理OR展开"""
        cond_sql = cond.sql()

        # 检查是否有顶级OR
        if self._has_top_level_or_in_expr(cond):
            or_parts = self._split_or_in_expr(cond)
            return '\n       '.join(or_parts)  # OR 与 WHERE 对齐

        return cond_sql

    def _has_top_level_or_in_expr(self, expr: exp.Expression) -> bool:
        """检查表达式是否有顶级OR"""
        if isinstance(expr, exp.Or):
            return True
        if isinstance(expr, exp.And):
            return (self._has_top_level_or_in_expr(expr.left) or
                    self._has_top_level_or_in_expr(expr.right))
        return False

    def _split_or_in_expr(self, expr: exp.Expression) -> list:
        """提取OR连接的条件"""
        if isinstance(expr, exp.Or):
            left = self._split_or_in_expr(expr.left)
            right = self._split_or_in_expr(expr.right)
            return left + right
        elif isinstance(expr, exp.And):
            # AND 的优先级高于 OR，所以整体作为一个条件
            return [expr.sql()]
        else:
            return [expr.sql()]

    def _format_group_by(self, parsed: exp.Select) -> list:
        """
        格式化GROUP BY子句

        规范要求：
        - GROUP BY 与 SELECT 左对齐
        - 多个字段逗号前置
        """
        group = parsed.args.get('group')
        if not group:
            return []

        indent = ' ' * self.indent_spaces
        lines = [f'\nGROUP BY']

        # 提取分组字段
        group_exprs = group.expressions if hasattr(group, 'expressions') else [group]

        for i, expr in enumerate(group_exprs):
            expr_sql = expr.sql()
            if i == 0:
                lines.append(f'{indent}    {expr_sql}')
            else:
                # 逗号前置，与 GROUP BY 中的 BY 对齐
                comma_indent = ' ' * len('GROUP BY')
                lines.append(f'{indent}{comma_indent}, {expr_sql}')

        return lines

    def _format_order_by(self, parsed: exp.Select) -> list:
        """
        格式化ORDER BY子句

        规范要求：
        - ORDER BY 与 SELECT 左对齐
        - 多个字段逗号前置
        """
        order = parsed.args.get('order')
        if not order:
            return []

        indent = ' ' * self.indent_spaces
        lines = [f'\nORDER BY']

        # 提取排序字段
        order_exprs = order.expressions if hasattr(order, 'expressions') else [order]

        for i, expr in enumerate(order_exprs):
            expr_sql = expr.sql()
            if i == 0:
                lines.append(f'{indent}    {expr_sql}')
            else:
                # 逗号前置
                comma_indent = ' ' * len('ORDER BY')
                lines.append(f'{indent}{comma_indent}, {expr_sql}')

        return lines

    def _format_having(self, having_expr: exp.Expression) -> list:
        """格式化HAVING子句（格式与WHERE类似）"""
        return self._format_where_conditions(having_expr)

    def _check_line_length(self, sql: str) -> str:
        """
        检查并处理超长行

        规范要求：每行不超过250字符
        """
        lines = sql.split('\n')
        processed_lines = []

        for line in lines:
            if len(line) <= self.max_line_length:
                processed_lines.append(line)
            else:
                # 行过长，尝试分割
                split_lines = self._split_long_line(line)
                processed_lines.extend(split_lines)

        return '\n'.join(processed_lines)

    def _split_long_line(self, line: str) -> list:
        """分割过长的行"""
        # 获取缩进
        indent_match = re.match(r'^(\s*)', line)
        base_indent = indent_match.group(1) if indent_match else ''

        result = []
        remaining = line

        while len(remaining) > self.max_line_length:
            # 寻找合适的分割点（优先逗号，其次空格）
            split_pos = remaining.rfind(',', 0, self.max_line_length)
            if split_pos == -1 or split_pos < len(base_indent):
                split_pos = remaining.rfind(' ', 0, self.max_line_length)

            if split_pos == -1 or split_pos < len(base_indent):
                # 强制分割
                split_pos = self.max_line_length
                result.append(remaining[:split_pos])
                remaining = base_indent + '    ' + remaining[split_pos:]
            else:
                # 在分割点后换行
                result.append(remaining[:split_pos + 1])
                remaining = base_indent + '    ' + remaining[split_pos + 1:].lstrip()

        if remaining:
            result.append(remaining)

        return result

    def _uppercase_keywords(self, sql: str) -> str:
        """关键字大写"""
        # 按长度排序，优先匹配长的关键字
        keywords = sorted(self.KEYWORDS_UPPER, key=len, reverse=True)
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            sql = re.sub(pattern, keyword, sql, flags=re.IGNORECASE)
        return sql

    def _remove_middle_blank_lines(self, sql: str) -> str:
        """去除中间的无意义空行"""
        lines = sql.split('\n')

        # 找到第一个和最后一个非空行
        first_non_empty = 0
        last_non_empty = len(lines) - 1

        while first_non_empty < len(lines) and not lines[first_non_empty].strip():
            first_non_empty += 1

        while last_non_empty >= 0 and not lines[last_non_empty].strip():
            last_non_empty -= 1

        if first_non_empty >= len(lines):
            return sql

        # 去除中间空行
        result = []

        # 保留开头空行
        for i in range(first_non_empty):
            result.append(lines[i])

        # 中间部分去除空行
        for i in range(first_non_empty, last_non_empty + 1):
            if lines[i].strip():
                result.append(lines[i])

        # 保留结尾空行
        for i in range(last_non_empty + 1, len(lines)):
            result.append(lines[i])

        return '\n'.join(result)


# 全局实例
_formatter_v2 = None


def format_sql_v2(sql: str, **options) -> str:
    """
    格式化SQL语句（符合开发规范版本）

    Args:
        sql: 原始SQL语句
        **options: 格式化选项
            - indent: 缩进空格数（默认4）
            - max_line_length: 最大行长度（默认250）
            - keyword_case: 关键字大小写（默认upper）
            - semicolon_newline: 分号另起一行（默认True）

    Returns:
        格式化后的SQL字符串
    """
    global _formatter_v2
    if _formatter_v2 is None:
        _formatter_v2 = SQLFormatterV2()

    # 更新配置
    indent = options.get('indent', 4)
    max_line_length = options.get('max_line_length', 250)

    if indent != 4 or max_line_length != 250:
        _formatter_v2 = SQLFormatterV2(indent_spaces=indent, max_line_length=max_line_length)

    return _formatter_v2.format(sql, **options)


if __name__ == "__main__":
    # 测试用例
    test_sql = """
    SELECT t1.column1,t2.column2,NVL(t1.column3,'') as col3,t1.id,t1.status from table1 t1 left join table2 t2 on t1.id=t2.id and t2.status='1' where t1.date>='2024-01-01' and t1.status in ('1','2') order by t1.id desc limit 100
    """

    print("=" * 60)
    print("原始SQL:")
    print("=" * 60)
    print(test_sql)

    print("\n" + "=" * 60)
    print("格式化后SQL:")
    print("=" * 60)
    formatted = format_sql_v2(test_sql)
    print(formatted)

    # 测试CASE WHEN
    test_case_sql = """
    select case when status='1' then 'active' when status='2' then 'inactive' else 'unknown' end as status_desc from users
    """

    print("\n" + "=" * 60)
    print("CASE WHEN 测试:")
    print("=" * 60)
    print(format_sql_v2(test_case_sql))

# -*- coding: utf-8 -*-
"""
SQL Formatter V5 - 修复多语句支持
基于 V4，增加：
1. 多SQL语句分割（按分号）
2. 支持 INSERT/CREATE/DROP 等语句类型
3. 保持注释不丢失
"""
import re
from typing import List, Dict, Tuple


def format_sql_v5(sql: str, **options) -> str:
    """
    格式化SQL，支持多语句
    """
    keyword_case = options.get('keyword_case', 'upper')

    # Step 1: 保护注释
    sql_protected, comment_map = _protect_comments(sql)

    # Step 2: 分割多个SQL语句（按分号，但要尊重括号和字符串）
    statements = _split_statements(sql_protected)

    # Step 3: 分别格式化每个语句
    formatted_statements = []
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        # 识别语句类型
        stmt_type = _identify_statement_type(stmt)

        if stmt_type == 'SELECT':
            formatted = _format_select_statement(stmt, keyword_case)
        elif stmt_type == 'INSERT':
            formatted = _format_insert_statement(stmt, keyword_case)
        elif stmt_type == 'CREATE':
            formatted = _format_create_statement(stmt, keyword_case)
        elif stmt_type == 'DROP':
            formatted = _format_drop_statement(stmt, keyword_case)
        else:
            # 其他类型保持原样（只做基本清理）
            formatted = _format_generic_statement(stmt, keyword_case)

        formatted_statements.append(formatted)

    # Step 4: 合并结果
    result = '\n\n'.join(formatted_statements)

    # Step 5: 恢复注释
    result = _restore_protected_comments(result, comment_map)

    # Step 6: 关键字大写
    if keyword_case == 'upper':
        result = _uppercase_keywords(result)

    return result


def _protect_comments(sql: str) -> tuple:
    """保护注释，替换为占位符"""
    comment_map = {}
    protected = sql
    counter = [0]

    def replace_comment(match):
        placeholder = f"__COMMENT_{counter[0]}__"
        comment_map[placeholder] = match.group(0)
        counter[0] += 1
        return placeholder

    # 保护块注释 /* ... */
    protected = re.sub(r'/\*.*?\*/', replace_comment, protected, flags=re.DOTALL)

    # 保护行注释 -- ...
    protected = re.sub(r'--[^\n]*', replace_comment, protected)

    return protected, comment_map


def _restore_protected_comments(sql: str, comment_map: dict) -> str:
    """恢复注释"""
    result = sql
    for placeholder, comment in comment_map.items():
        result = result.replace(placeholder, comment)
    return result


def _split_statements(sql: str) -> List[str]:
    """按分号分割SQL语句，尊重括号、字符串和注释占位符"""
    statements = []
    current = ''
    depth = 0
    in_string = False
    string_char = None
    i = 0

    while i < len(sql):
        char = sql[i]

        # 处理字符串
        if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
            current += char
            i += 1
            continue

        if in_string:
            current += char
            i += 1
            continue

        # 处理括号
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ';' and depth == 0:
            # 分号且不在括号内 - 语句结束
            if current.strip():
                statements.append(current.strip())
            current = ''
        else:
            current += char

        i += 1

    # 添加最后一个语句（如果没有分号结尾）
    if current.strip():
        statements.append(current.strip())

    return statements


def _identify_statement_type(stmt: str) -> str:
    """识别SQL语句类型"""
    stmt_upper = stmt.strip().upper()

    # 跳过注释占位符
    stmt_clean = re.sub(r'__COMMENT_\d+__', '', stmt_upper).strip()

    if stmt_clean.startswith('INSERT'):
        return 'INSERT'
    elif stmt_clean.startswith('SELECT'):
        return 'SELECT'
    elif stmt_clean.startswith('CREATE'):
        return 'CREATE'
    elif stmt_clean.startswith('DROP'):
        return 'DROP'
    elif stmt_clean.startswith('UPDATE'):
        return 'UPDATE'
    elif stmt_clean.startswith('DELETE'):
        return 'DELETE'
    else:
        return 'OTHER'


def _format_select_statement(stmt: str, keyword_case: str) -> str:
    """格式化 SELECT 语句"""
    parts = _parse_select_parts(stmt)

    lines = []

    # SELECT 子句
    if parts['select']:
        select_lines = _format_select_fields(parts['select'])
        lines.extend(select_lines)

    # FROM 子句
    if parts['from']:
        lines.append(f"FROM {parts['from']}")

    # JOIN 子句
    for join in parts['joins']:
        join_lines = _format_join(join)
        lines.extend(join_lines)

    # WHERE 子句
    if parts['where']:
        where_lines = _format_where(parts['where'])
        lines.extend(where_lines)

    # GROUP BY 子句
    if parts['group_by']:
        lines.append(f"    GROUP BY {parts['group_by']}")

    # ORDER BY 子句
    if parts['order_by']:
        lines.append(f"    ORDER BY {parts['order_by']}")

    # DISTRIBUTE BY 子句
    if parts['distribute_by']:
        lines.append(f"DISTRIBUTE BY {parts['distribute_by']}")

    return '\n'.join(lines)


def _format_insert_statement(stmt: str, keyword_case: str) -> str:
    """格式化 INSERT 语句"""
    lines = []

    # 解析 INSERT ... SELECT 结构
    insert_match = re.match(
        r'(INSERT\s+INTO\s+\S+)\s*(.*)',
        stmt,
        re.IGNORECASE | re.DOTALL
    )

    if insert_match:
        insert_clause = insert_match.group(1)
        rest = insert_match.group(2).strip()

        lines.append(insert_clause)

        # 检查后面是否是 SELECT
        if re.match(r'\bSELECT\b', rest, re.IGNORECASE):
            select_formatted = _format_select_statement(rest, keyword_case)
            # 缩进 SELECT 部分
            for sl in select_formatted.split('\n'):
                lines.append('    ' + sl if sl.strip() else sl)
        else:
            lines.append('    ' + rest)
    else:
        # 无法解析，保持原样
        lines.append(stmt)

    return '\n'.join(lines)


def _format_create_statement(stmt: str, keyword_case: str) -> str:
    """格式化 CREATE 语句"""
    lines = []

    # CREATE TABLE ... AS SELECT
    create_as_match = re.match(
        r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+)\s+AS\s+(SELECT\s+.*)',
        stmt,
        re.IGNORECASE | re.DOTALL
    )

    if create_as_match:
        create_clause = create_as_match.group(1)
        select_part = create_as_match.group(2)

        lines.append(create_clause + ' AS')
        select_formatted = _format_select_statement(select_part, keyword_case)
        for sl in select_formatted.split('\n'):
            lines.append('    ' + sl if sl.strip() else sl)
        return '\n'.join(lines)

    # CREATE TABLE with columns
    create_match = re.match(
        r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+))\s*\((.*)\)(.*)',
        stmt,
        re.IGNORECASE | re.DOTALL
    )

    if create_match:
        create_clause = create_match.group(1)
        columns_str = create_match.group(3)
        table_options = create_match.group(4).strip()

        lines.append(create_clause)
        lines.append('(')

        # 解析列定义
        columns = _split_columns(columns_str)
        for i, col in enumerate(columns):
            col = col.strip()
            if col:
                comma = ',' if i < len(columns) - 1 else ''
                lines.append(f"    {col}{comma}")

        lines.append(')')

        if table_options:
            lines.append(table_options)

        return '\n'.join(lines)

    # 无法解析，保持原样
    return stmt


def _format_drop_statement(stmt: str, keyword_case: str) -> str:
    """格式化 DROP 语句"""
    # DROP 语句通常很简单，保持在一行
    return stmt


def _format_generic_statement(stmt: str, keyword_case: str) -> str:
    """格式化通用语句"""
    return stmt


def _split_columns(columns_str: str) -> List[str]:
    """分割列定义，尊重括号"""
    columns = []
    current = ''
    depth = 0

    for char in columns_str:
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            columns.append(current.strip())
            current = ''
        else:
            current += char

    if current.strip():
        columns.append(current.strip())

    return columns


def _parse_select_parts(sql: str) -> Dict:
    """解析 SELECT 语句的各个部分"""
    parts = {
        'select': [],
        'from': '',
        'joins': [],
        'where': '',
        'group_by': '',
        'order_by': '',
        'distribute_by': ''
    }

    # 保护子查询
    protected_sql = sql
    placeholders = {}

    # 保护括号中的子查询
    paren_depth = 0
    paren_start = -1
    i = 0
    while i < len(protected_sql):
        if protected_sql[i] == '(':
            if paren_depth == 0:
                paren_start = i
            paren_depth += 1
        elif protected_sql[i] == ')':
            paren_depth -= 1
            if paren_depth == 0 and paren_start >= 0:
                paren_content = protected_sql[paren_start:i+1]
                if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                    placeholder = f"__SUBQUERY_{len(placeholders)}__"
                    placeholders[placeholder] = paren_content
                    protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                    i = -1
                    paren_depth = 0
                    paren_start = -1
        i += 1

    # 查找子句边界
    clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'
    matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

    for i, match in enumerate(matches):
        clause_type = match.group(1).upper().replace(' ', '_')
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
        clause_content = protected_sql[start:end].strip().rstrip(',')

        # 恢复占位符
        for placeholder, original in placeholders.items():
            clause_content = clause_content.replace(placeholder, original)

        if clause_type == 'SELECT':
            parts['select'] = _parse_select_fields(clause_content)
        elif clause_type == 'FROM':
            parts['from'] = clause_content
        elif 'JOIN' in clause_type:
            parts['joins'].append({
                'type': match.group(1).upper(),
                'content': clause_content
            })
        elif clause_type == 'WHERE':
            parts['where'] = clause_content
        elif clause_type == 'GROUP_BY':
            parts['group_by'] = clause_content
        elif clause_type == 'ORDER_BY':
            parts['order_by'] = clause_content
        elif clause_type == 'DISTRIBUTE_BY':
            parts['distribute_by'] = clause_content

    return parts


def _parse_select_fields(fields_str: str) -> List[str]:
    """解析 SELECT 字段列表"""
    fields = []
    current = ''
    depth = 0
    in_string = False
    string_char = None

    for i, char in enumerate(fields_str):
        if char in ("'", '"') and (i == 0 or fields_str[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
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
            fields.append(current.strip())
            current = ''
        else:
            current += char

    if current.strip():
        fields.append(current.strip())

    return fields


def _format_select_fields(fields: List[str]) -> List[str]:
    """格式化 SELECT 字段（逗号前置风格）"""
    lines = []

    for i, field in enumerate(fields):
        field = field.strip()
        if not field:
            continue

        # 检查是否包含 CASE
        if re.search(r'\bCASE\b', field, re.IGNORECASE):
            field_formatted = _format_case_field(field)
        else:
            field_formatted = field

        if i == 0:
            lines.append(f"SELECT {field_formatted}")
        else:
            lines.append(f"     , {field_formatted}")

    return lines


def _format_case_field(field: str) -> str:
    """格式化包含 CASE 的字段"""
    # 提取别名
    alias_match = re.search(r'\s+AS\s+(\w+)\s*$', field, re.IGNORECASE)
    alias = alias_match.group(1) if alias_match else None
    if alias_match:
        field = field[:alias_match.start()].strip()

    # 移除外层括号（如果整个 CASE 被括号包裹）
    if field.startswith('(') and field.endswith(')'):
        inner = field[1:-1].strip()
        if re.match(r'^CASE\b', inner, re.IGNORECASE):
            field = inner

    # 格式化 CASE
    case_formatted = _format_case(field)

    if alias:
        return f"{case_formatted}\n    AS {alias}"
    return case_formatted


def _format_case(case_sql: str) -> str:
    """格式化 CASE 表达式"""
    case_sql = case_sql.strip()

    if not case_sql.upper().startswith('CASE'):
        return case_sql

    # 找到 CASE 和 END 的边界
    depth = 0
    end_pos = -1
    content_start = 4

    for i in range(len(case_sql)):
        if case_sql[i:i+4].upper() == 'CASE' and (i == 0 or not case_sql[i-1].isalnum()):
            depth += 1
        elif case_sql[i:i+3].upper() == 'END' and (i+3 >= len(case_sql) or not case_sql[i+3].isalnum()):
            depth -= 1
            if depth == 0:
                end_pos = i
                break

    if end_pos == -1:
        return case_sql

    inner_content = case_sql[content_start:end_pos].strip()

    # 解析 WHEN-THEN 和 ELSE
    parts = _parse_case_parts(inner_content)

    indent = '       '  # CASE 内容缩进
    lines = ['CASE']

    for when_cond, then_val in parts['whens']:
        lines.append(f'{indent}WHEN {when_cond.strip()}')
        lines.append(f'{indent}THEN {then_val.strip()}')

    if parts['else']:
        lines.append(f'{indent}ELSE {parts["else"].strip()}')

    lines.append('    END')

    return '\n'.join(lines)


def _parse_case_parts(content: str) -> Dict:
    """解析 CASE 的 WHEN-THEN 和 ELSE 部分"""
    parts = {
        'whens': [],
        'else': ''
    }

    # 使用 token 解析
    tokens = re.split(r'(\bWHEN\b|\bTHEN\b|\bELSE\b|\bCASE\b|\bEND\b|\(|\))', content, flags=re.IGNORECASE)

    current_when = ''
    current_then = ''
    in_when = False
    in_then = False
    case_depth = 0
    paren_depth = 0

    for token in tokens:
        token_upper = token.upper() if token else ''

        if token == '(':
            paren_depth += 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token == ')':
            paren_depth -= 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'CASE':
            case_depth += 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'END':
            case_depth -= 1
            if in_when:
                current_when += token
            elif in_then:
                current_then += token
        elif token_upper == 'WHEN' and case_depth == 0 and paren_depth == 0:
            if current_when and current_then:
                parts['whens'].append((current_when.strip(), current_then.strip()))
            current_when = ''
            current_then = ''
            in_when = True
            in_then = False
        elif token_upper == 'THEN' and case_depth == 0 and paren_depth == 0:
            in_when = False
            in_then = True
        elif token_upper == 'ELSE' and case_depth == 0 and paren_depth == 0:
            if current_when and current_then:
                parts['whens'].append((current_when.strip(), current_then.strip()))
            in_when = False
            in_then = False
            # 收集剩余内容作为 ELSE
            else_content = content[content.upper().find('ELSE', len(content) - len(' '.join(tokens))):]
            else_content = re.sub(r'^\s*ELSE\s*', '', else_content, flags=re.IGNORECASE)
            parts['else'] = else_content.strip()
            break
        else:
            if in_when:
                current_when += token
            elif in_then:
                current_then += token

    # 添加最后一个 WHEN-THEN
    if current_when.strip() and current_then.strip():
        parts['whens'].append((current_when.strip(), current_then.strip()))

    return parts


def _format_join(join: Dict) -> List[str]:
    """格式化 JOIN 子句"""
    lines = []
    join_type = join['type']
    content = join['content']

    # 检查是否有 ON 条件
    on_match = re.search(r'\bON\b\s+(.+)$', content, re.IGNORECASE | re.DOTALL)

    if on_match:
        table = content[:on_match.start()].strip()
        on_condition = on_match.group(1).strip()

        lines.append(f"    {join_type} {table}")
        lines.append(f"        ON {on_condition}")
    else:
        lines.append(f"    {join_type} {content}")

    return lines


def _format_where(where: str) -> List[str]:
    """格式化 WHERE 子句"""
    lines = []

    # 分割 AND 条件
    conditions = _split_by_logical_op(where, 'AND')

    if conditions:
        first = conditions[0].strip()
        lines.append(f"    WHERE {first}")

        for cond in conditions[1:]:
            cond = cond.strip()
            lines.append(f"        AND {cond}")

    return lines


def _split_by_logical_op(sql: str, op: str) -> List[str]:
    """按逻辑运算符分割，尊重括号和 CASE"""
    conditions = []
    current = ''
    paren_depth = 0
    case_depth = 0

    tokens = re.split(rf'(\b{op}\b|\(|\)|\bCASE\b|\bEND\b)', sql, flags=re.IGNORECASE)

    for token in tokens:
        token_upper = token.upper() if token else ''

        if token == '(':
            paren_depth += 1
            current += token
        elif token == ')':
            paren_depth -= 1
            current += token
        elif token_upper == 'CASE':
            case_depth += 1
            current += token
        elif token_upper == 'END':
            case_depth -= 1
            current += token
        elif token_upper == op and paren_depth == 0 and case_depth == 0:
            if current.strip():
                conditions.append(current.strip())
            current = ''
        else:
            current += token

    if current.strip():
        conditions.append(current.strip())

    return conditions


def _uppercase_keywords(sql: str) -> str:
    """关键字大写"""
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'EXISTS',
        'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'JOIN', 'ON',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'DISTRIBUTE BY',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'IS', 'NULL',
        'LIKE', 'BETWEEN', 'DISTINCT', 'OVER', 'PARTITION BY',
        'ASC', 'DESC', 'NVL', 'CAST', 'SUBSTR', 'SUBSTRING',
        'LPAD', 'RPAD', 'ROW_NUMBER', 'COALESCE', 'RAND', 'CEIL',
        'INSERT', 'INTO', 'CREATE', 'TABLE', 'DROP', 'IF', 'NOT',
        'EXISTS', 'COMMENT', 'STRING', 'INT', 'BIGINT', 'DOUBLE',
        'FORMAT', 'DELIMITED', 'NULL', 'DEFINED'
    ]

    result = sql
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = r'\b' + re.escape(keyword) + r'\b'
        result = re.sub(pattern, keyword.upper(), result, flags=re.IGNORECASE)

    return result


# 兼容性别名
format_sql_v4_fixed = format_sql_v5

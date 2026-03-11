# -*- coding: utf-8 -*-
"""
SQL Formatter V6 - 保守格式化器
设计目标：
1. 保持逗号前置风格（逗号在行首）
2. 保留所有SQL语句（不丢失内容）
3. 保留分号
4. 只做关键字大写和基本格式化
"""
import re
from typing import List, Tuple


def format_sql_v6(sql: str, **options) -> str:
    """
    保守的SQL格式化器
    - 保持原始结构
    - 保持逗号前置风格
    - 保留所有语句和分号
    - 只做关键字大写
    """
    keyword_case = options.get('keyword_case', 'upper')

    # Step 1: 保护注释
    sql_protected, comment_map = _protect_comments(sql)

    # Step 2: 按分号分割语句（保留分号）
    statements = _split_statements_with_semicolon(sql_protected)

    # Step 3: 格式化每个语句
    formatted_statements = []
    for stmt, has_semicolon in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        # 格式化单个语句（保持原有结构）
        formatted = _format_single_statement(stmt)

        # 恢复分号
        if has_semicolon:
            formatted = formatted.rstrip() + ';'

        formatted_statements.append(formatted)

    # Step 4: 合并结果
    result = '\n\n'.join(formatted_statements)

    # Step 5: 恢复注释
    result = _restore_comments(result, comment_map)

    # Step 6: 关键字大写
    if keyword_case == 'upper':
        result = _uppercase_keywords(result)

    return result


def _protect_comments(sql: str) -> Tuple[str, dict]:
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


def _restore_comments(sql: str, comment_map: dict) -> str:
    """恢复注释"""
    result = sql
    for placeholder, comment in comment_map.items():
        result = result.replace(placeholder, comment)
    return result


def _split_statements_with_semicolon(sql: str) -> List[Tuple[str, bool]]:
    """按分号分割SQL语句，保留分号信息"""
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
                statements.append((current.strip(), True))
            current = ''
        else:
            current += char

        i += 1

    # 添加最后一个语句（如果没有分号结尾）
    if current.strip():
        statements.append((current.strip(), False))

    return statements


def _format_single_statement(stmt: str) -> str:
    """格式化单个SQL语句，保持原有结构"""
    # 识别语句类型
    stmt_type = _get_statement_type(stmt)

    if stmt_type == 'CREATE_TABLE':
        return _format_create_table(stmt)
    elif stmt_type == 'INSERT_SELECT':
        return _format_insert_select(stmt)
    elif stmt_type == 'SELECT':
        return _format_select(stmt)
    elif stmt_type == 'DROP':
        return _format_drop(stmt)
    elif stmt_type == 'CREATE_TABLE_AS':
        return _format_create_table_as(stmt)
    else:
        # 其他类型保持原样
        return stmt


def _get_statement_type(stmt: str) -> str:
    """识别SQL语句类型"""
    stmt_upper = stmt.strip().upper()

    # 移除注释占位符
    stmt_clean = re.sub(r'__COMMENT_\d+__', '', stmt_upper).strip()

    if stmt_clean.startswith('DROP'):
        return 'DROP'
    elif re.match(r'^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+\s*AS\s+SELECT\b', stmt_clean, re.IGNORECASE):
        return 'CREATE_TABLE_AS'
    elif re.match(r'^CREATE\s+TABLE', stmt_clean):
        return 'CREATE_TABLE'
    elif stmt_clean.startswith('INSERT'):
        if 'SELECT' in stmt_clean:
            return 'INSERT_SELECT'
        return 'INSERT'
    elif stmt_clean.startswith('SELECT'):
        return 'SELECT'
    else:
        return 'OTHER'


def _format_drop(stmt: str) -> str:
    """格式化 DROP 语句 - 保持原样"""
    return stmt


def _format_create_table(stmt: str) -> str:
    """格式化 CREATE TABLE 语句，保持逗号前置风格"""
    # 匹配 CREATE TABLE ... ( ... ) ...
    match = re.match(
        r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+)\s*\((.*)\)(.*)',
        stmt,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return stmt

    create_header = match.group(1)
    columns_str = match.group(2)
    table_options = match.group(3).strip()

    # 解析列定义，保持逗号前置风格
    lines = [create_header, '(']

    # 分割列定义
    column_lines = _split_column_definitions(columns_str)

    for i, col in enumerate(column_lines):
        col = col.strip()
        if col:
            # 如果原本是逗号前置，保持逗号前置
            if col.startswith(','):
                lines.append(col)
            elif i == 0:
                # 第一行不加逗号
                lines.append(' ' + col)
            else:
                # 其他行加逗号前置
                lines.append(',' + col)

    lines.append(')')

    if table_options:
        lines.append(table_options)

    return '\n'.join(lines)


def _split_column_definitions(columns_str: str) -> List[str]:
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


def _format_insert_select(stmt: str) -> str:
    """格式化 INSERT ... SELECT 语句"""
    # 匹配 INSERT INTO ... SELECT ...
    match = re.match(
        r'(INSERT\s+INTO\s+(?:TABLE\s+)?\S+)(\s*\(.*\))?\s*(SELECT\s+.*)',
        stmt,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        # 尝试简单匹配
        match = re.match(
            r'(INSERT\s+INTO\s+(?:TABLE\s+)?\S+)\s*(SELECT\s+.*)',
            stmt,
            re.IGNORECASE | re.DOTALL
        )
        if not match:
            return stmt

        insert_header = match.group(1)
        select_part = match.group(2)

        lines = [insert_header]
        select_formatted = _format_select(select_part)
        for sl in select_formatted.split('\n'):
            lines.append(sl)

        return '\n'.join(lines)

    insert_header = match.group(1)
    columns = match.group(2) or ''
    select_part = match.group(3)

    lines = [insert_header]
    if columns:
        lines.append(columns.strip())

    select_formatted = _format_select(select_part)
    for sl in select_formatted.split('\n'):
        lines.append(sl)

    return '\n'.join(lines)


def _format_select(stmt: str) -> str:
    """格式化 SELECT 语句，保持逗号前置风格"""
    # 保护子查询
    protected, placeholders = _protect_subqueries(stmt)

    # 找到 SELECT, FROM, WHERE, GROUP BY, JOIN 等子句
    parts = _parse_select_clauses(protected)

    lines = []

    # SELECT 子句
    if parts['select']:
        select_fields = parts['select']
        # 检查原始格式是否是逗号前置
        is_comma_first = any(f.strip().startswith(',') for f in select_fields if f.strip())

        for i, field in enumerate(select_fields):
            field = field.strip()
            if not field:
                continue

            # 恢复子查询占位符
            for ph, original in placeholders.items():
                field = field.replace(ph, original)

            if i == 0:
                # 第一个字段：SELECT field
                if field.startswith(','):
                    field = field[1:].strip()
                lines.append(f'SELECT {field}')
            else:
                # 后续字段：保持或添加逗号前置
                if not field.startswith(','):
                    field = ',' + field
                lines.append(field)

    # FROM 子句
    if parts['from']:
        from_content = parts['from']
        for ph, original in placeholders.items():
            from_content = from_content.replace(ph, original)
        lines.append(f'FROM {from_content}')

    # JOIN 子句
    for join in parts['joins']:
        join_content = join
        for ph, original in placeholders.items():
            join_content = join_content.replace(ph, original)
        lines.append(join_content)

    # WHERE 子句
    if parts['where']:
        where_content = parts['where']
        for ph, original in placeholders.items():
            where_content = where_content.replace(ph, original)
        lines.append(f'WHERE {where_content}')

    # GROUP BY 子句
    if parts['group_by']:
        lines.append(f'GROUP BY {parts["group_by"]}')

    return '\n'.join(lines)


def _protect_subqueries(sql: str) -> Tuple[str, dict]:
    """保护子查询"""
    placeholders = {}
    protected = sql

    # 找到括号中的子查询
    paren_depth = 0
    paren_start = -1
    i = 0

    while i < len(protected):
        if protected[i] == '(':
            if paren_depth == 0:
                paren_start = i
            paren_depth += 1
        elif protected[i] == ')':
            paren_depth -= 1
            if paren_depth == 0 and paren_start >= 0:
                paren_content = protected[paren_start:i+1]
                if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                    placeholder = f"__SUBQUERY_{len(placeholders)}__"
                    placeholders[placeholder] = paren_content
                    protected = protected[:paren_start] + placeholder + protected[i+1:]
                    i = paren_start + len(placeholder) - 1
                    paren_start = -1
        i += 1

    return protected, placeholders


def _parse_select_clauses(sql: str) -> dict:
    """解析 SELECT 语句的各个子句"""
    parts = {
        'select': [],
        'from': '',
        'joins': [],
        'where': '',
        'group_by': ''
    }

    # 匹配子句边界
    clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|JOIN|WHERE|GROUP\s+BY)\b'
    matches = list(re.finditer(clause_pattern, sql, re.IGNORECASE))

    for i, match in enumerate(matches):
        clause_type = match.group(1).upper().replace(' ', '_')
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(sql)
        clause_content = sql[start:end].strip().rstrip(',')

        if clause_type == 'SELECT':
            parts['select'] = _split_select_fields(clause_content)
        elif clause_type == 'FROM':
            parts['from'] = clause_content
        elif 'JOIN' in clause_type:
            parts['joins'].append(f"{match.group(1).upper()} {clause_content}")
        elif clause_type == 'WHERE':
            parts['where'] = clause_content
        elif clause_type == 'GROUP_BY':
            parts['group_by'] = clause_content

    return parts


def _split_select_fields(fields_str: str) -> List[str]:
    """分割 SELECT 字段，保持逗号前置格式"""
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


def _format_create_table_as(stmt: str) -> str:
    """格式化 CREATE TABLE AS SELECT 语句"""
    match = re.match(
        r'(CREATE\s+TABLE\s+\S+)\s+AS\s+(SELECT\s+.*)',
        stmt,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return stmt

    create_header = match.group(1)
    select_part = match.group(2)

    lines = [create_header + ' AS']
    select_formatted = _format_select(select_part)
    for sl in select_formatted.split('\n'):
        lines.append(sl)

    return '\n'.join(lines)


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
        'FORMAT', 'DELIMITED', 'DEFINED', 'SUM', 'COUNT', 'MAX', 'MIN', 'AVG'
    ]

    result = sql
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = r'\b' + re.escape(keyword) + r'\b'
        result = re.sub(pattern, keyword.upper(), result, flags=re.IGNORECASE)

    return result

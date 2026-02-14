"""
测试CASE WHEN格式化功能
"""

import re

def format_case_when(case_field: str, has_comma: bool = False) -> list:
    """格式化CASE WHEN字段"""
    lines = []

    # 提取CASE和表达式
    case_match = re.match(r'(CASE\s+.*?)(\s+END\b)', case_field, re.IGNORECASE)
    if not case_match:
        # 不是CASE WHEN，按普通字段处理
        comma = '     ,' if has_comma else '      '
        return [f"{comma}{case_field}"]

    full_case = case_match.group(1) if case_match else ''
    inner = full_case[4:-4].strip() if case_match else ''

    # 分割WHEN/THEN/ELSE
    parts = split_case_when_parts(inner)

    # 格式化第一行
    if has_comma:
        lines.append('     , CASE')
    else:
        lines.append('      CASE')

    # WHEN/THEN/ELSE的缩进，比CASE多一级
    base_indent = '         '

    for j, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        if part.upper().startswith('WHEN '):
            when_match = re.match(r'WHEN\s+(.+?)\s+THEN', part, re.IGNORECASE)
            if when_match:
                condition = when_match.group(1).strip()
                then_value = when_match.group(2).strip()
                lines.append(f"{base_indent}     {condition}")
                lines.append(f"{base_indent}     THEN {then_value}")
        elif part.upper() == 'ELSE':
            lines.append(f"{base_indent}     ELSE")
        elif part.upper() == 'END':
            # 提取别名部分（AS alias）
            alias_part = part[4:]
            alias = alias.strip()
            if alias.upper().startswith('AS '):
                alias = alias[2:].strip()
                lines.append(f"{base_indent}END{alias}")

    return lines


def split_case_when_parts(case_inner: str) -> list:
    """分割CASE WHEN内部的WHEN/THEN/ELSE部分"""
    parts = []
    depth = 0
    in_string = False
    str_char = None
    current = []
    i = 0

    while i < len(case_inner):
        char = case_inner[i]

        if char in ("'", '"') and (i == 0 or case_inner[i-1] != '\\'):
            if not in_string:
                in_string = True
                str_char = char
            elif char == str_char:
                in_string = False

        if in_string:
            current.append(char)
            i += 1
            continue

        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1

        if depth == 0:
            # 检查AND/OR（用于分割WHEN/ELSE）
            if re.match(r'\b(AND|OR)\b', case_inner[i:], re.IGNORECASE):
                # 保存之前的内容
                if current:
                    parts.append(''.join(current).strip())
                current = []
                i += 3  # 跳过AND/OR
                continue

        current.append(char)
        i += 1

    # 添加剩余内容
    remaining = ''.join(current).strip()
    if remaining:
        parts.append(remaining)

    return parts


if __name__ == '__main__':
    # 测试SQL
    test_sql = '''
    SELECT
        aa
     , CASE
             WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTE'
             THEN '01'
         WHEN SUBSTR(t8.cdpt_accno,1,3) = 'FTN'
             THEN '02'
         ELSE ''
         END AS acctype
        , '1' AS customtype
    FROM table1
'''

    print("=== 测试SQL ===")
    print(test_sql)
    print()

    result = format_case_when(test_sql, has_comma=True)
    print("\n格式化结果:")
    for line in result:
        print(line)

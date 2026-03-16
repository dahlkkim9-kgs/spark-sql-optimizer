# -*- coding: utf-8 -*-
"""模拟 _parse_sql_parts 的处理过程"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 模拟外层子查询的内容（去括号后）
sql = """SELECT *
FROM table1
WHERE col NOT IN (
    SELECT id FROM table2
)"""

print("=" * 80)
print("模拟 _parse_sql_parts 处理")
print("=" * 80)
print(f"输入SQL:\n{sql}\n")

# 步骤1: 保护子查询
print("步骤1: 保护子查询")
protected_sql = sql
placeholders = {}
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
                print(f"  保护 {placeholder}: {repr(paren_content)}")
                protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                i = -1
                paren_depth = 0
                paren_start = -1
    i += 1

print(f"\n保护后的SQL:\n{protected_sql}")
print(f"\n占位符: {list(placeholders.keys())}")
print()

# 步骤2: 解析子句
print("步骤2: 解析子句")
clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'
matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

parts = {'select': [], 'from': '', 'joins': [], 'where': '', 'group_by': '', 'order_by': '', 'distribute_by': ''}

for i, match in enumerate(matches):
    clause_type = match.group(1).upper().replace(' ', '_')
    start = match.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
    raw_content = protected_sql[start:end]
    clause_content = raw_content.strip().rstrip(',')

    print(f"\n子句: {clause_type}")
    print(f"  内容: {repr(clause_content)}")

    # 步骤3: 恢复占位符
    if '__SUBQUERY_' in clause_content:
        print(f"  包含子查询占位符，开始恢复...")

        for placeholder, original in placeholders.items():
            if placeholder in clause_content:
                print(f"    处理占位符: {placeholder}")
                print(f"      原始内容: {repr(original)}")

                # 查找占位符位置
                placeholder_pos = clause_content.find(placeholder)
                before_placeholder = clause_content[:placeholder_pos]
                after_placeholder = clause_content[placeholder_pos + len(placeholder):]

                print(f"      占位符前: {repr(before_placeholder)}")
                print(f"      占位符后: {repr(after_placeholder)}")

                # 检测 IN 模式
                in_pattern = re.search(r'\b(IN|NOT IN|EXISTS)\s*$', before_placeholder, re.IGNORECASE)
                if in_pattern:
                    print(f"      检测到 IN 模式: {in_pattern.group(1)}")

                    # 计算缩进
                    clause_keyword_len = len('WHERE ') if clause_type == 'WHERE' else 0
                    open_paren_pos = clause_keyword_len + len(before_placeholder)
                    subquery_indent = ' ' * (open_paren_pos + 1)
                    close_paren_indent = ' ' * open_paren_pos

                    print(f"      开括号位置: {open_paren_pos}")
                    print(f"      子查询缩进: {len(subquery_indent)} 空格")
                    print(f"      闭括号缩进: {len(close_paren_indent)} 空格")

                    # 模拟替换
                    # 假设格式化后的子查询
                    formatted_subquery = "SELECT id\nFROM table2"
                    indented_subquery = '\n'.join(subquery_indent + line if line.strip() else line for line in formatted_subquery.split('\n'))

                    replacement = '(\n' + indented_subquery + '\n' + close_paren_indent + ')'
                    clause_content = clause_content.replace(placeholder, replacement)

                    print(f"      替换后内容:")
                    for line in clause_content.split('\n'):
                        print(f"        {repr(line)}")

        # 保存到 parts
        parts['where'] = clause_content

print()
print("=" * 80)
print("最终 parts['where'] 内容:")
print(repr(parts['where']))
print()
print("实际输出:")
print(parts['where'])

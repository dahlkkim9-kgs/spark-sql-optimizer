# -*- coding: utf-8 -*-
"""详细调试格式化过程"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 简化的测试案例
test_sql = """SELECT *
FROM (
    SELECT *
    FROM table1
    WHERE col NOT IN (
        SELECT id FROM table2
    )
) xyk;"""

print("=" * 80)
print("格式化过程调试")
print("=" * 80)
print("原始SQL:")
print(test_sql)
print()

# 步骤1: 保护子查询
print("步骤1: 保护子查询")
protected_sql = test_sql
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
                print(f"  保护 {placeholder}: {repr(paren_content[:60])}")
                protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                i = -1
                paren_depth = 0
                paren_start = -1
    i += 1

print(f"\n保护后的SQL:\n{protected_sql}\n")
print(f"占位符数量: {len(placeholders)}")
for k, v in placeholders.items():
    print(f"  {k}: {len(v)} 字符")
print()

# 步骤2: 解析子句
print("步骤2: 解析子句")
clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'
matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

for i, match in enumerate(matches):
    clause_type = match.group(1).upper().replace(' ', '_')
    start = match.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
    raw_content = protected_sql[start:end]
    clause_content = raw_content.strip().rstrip(',')

    print(f"\n子句 {i+1}: {clause_type}")
    print(f"  内容: {repr(clause_content)}")

    # 步骤3: 恢复占位符
    if '__SUBQUERY_' in clause_content:
        print(f"  包含子查询占位符")
        for placeholder, original in placeholders.items():
            if placeholder in clause_content:
                print(f"    找到占位符: {placeholder}")
                placeholder_pos = clause_content.find(placeholder)
                before_placeholder = clause_content[:placeholder_pos]
                print(f"    占位符前: {repr(before_placeholder)}")

                # 模拟替换
                simulated_replacement = f"{before_placeholder}("
                print(f"    模拟替换后开头: {repr(simulated_replacement)}")
print()

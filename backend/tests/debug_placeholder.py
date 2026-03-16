# -*- coding: utf-8 -*-
"""调试占位符替换过程"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 模拟占位符保护过程
test_sql = """SELECT *
FROM (
    SELECT *
    FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XYK
    WHERE khzjdm NOT IN (
        SELECT DISTINCT khzjdm
        FROM rhbs_work.RHZF_GRKHJCXX_$TXDATE_XD
    )
) xyk;"""

print("=" * 80)
print("占位符保护过程调试")
print("=" * 80)
print("原始SQL:")
print(test_sql)
print()

# 模拟保护子查询
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
                print(f"发现子查询 {len(placeholders)}:")
                print(f"  内容: {repr(paren_content[:100])}")
                print(f"  占位符: {placeholder}")
                print()
                protected_sql = protected_sql[:paren_start] + placeholder + protected_sql[i+1:]
                i = -1
                paren_depth = 0
                paren_start = -1
    i += 1

print("保护后的SQL:")
print(protected_sql)
print()
print("占位符字典:")
for k, v in placeholders.items():
    print(f"  {k}: {repr(v[:80])}")
print()

# 现在模拟解析 WHERE 子句
clause_pattern = r'\b(SELECT|FROM|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|CROSS\s+JOIN|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|DISTRIBUTE\s+BY|HAVING|LIMIT)\b'
matches = list(re.finditer(clause_pattern, protected_sql, re.IGNORECASE))

print("子句匹配:")
for match in matches:
    print(f"  {match.group(1)}: 位置 {match.start()}-{match.end()}")
print()

# 找到 WHERE 子句
for i, match in enumerate(matches):
    if match.group(1).upper() == 'WHERE':
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(protected_sql)
        raw_content = protected_sql[start:end]
        clause_content = raw_content.strip().rstrip(',')

        print(f"WHERE 子句内容:")
        print(f"  原始: {repr(raw_content)}")
        print(f"  清理后: {repr(clause_content)}")
        print()

        # 检查占位符
        for placeholder, original in placeholders.items():
            if placeholder in clause_content:
                print(f"找到占位符: {placeholder}")
                print(f"  原始内容: {repr(original[:100])}")

                # 查找占位符位置
                placeholder_pos = clause_content.find(placeholder)
                before_placeholder = clause_content[:placeholder_pos]
                after_placeholder = clause_content[placeholder_pos + len(placeholder):]

                print(f"  占位符前: {repr(before_placeholder)}")
                print(f"  占位符后: {repr(after_placeholder)}")
                print()

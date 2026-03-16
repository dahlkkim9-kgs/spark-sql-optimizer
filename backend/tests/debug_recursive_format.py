# -*- coding: utf-8 -*-
"""模拟递归格式化过程"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 原始SQL
test_sql = """SELECT *
FROM (
    SELECT *
    FROM table1
    WHERE col NOT IN (
        SELECT id FROM table2
    )
) xyk;"""

print("=" * 80)
print("递归格式化过程模拟")
print("=" * 80)
print("原始SQL:")
print(test_sql)
print()

# ===== 第一层：保护外层子查询 =====
print("【第一层】保护外层子查询")
protected_sql_1 = test_sql
placeholders_1 = {}
paren_depth = 0
paren_start = -1
i = 0

while i < len(protected_sql_1):
    if protected_sql_1[i] == '(':
        if paren_depth == 0:
            paren_start = i
        paren_depth += 1
    elif protected_sql_1[i] == ')':
        paren_depth -= 1
        if paren_depth == 0 and paren_start >= 0:
            paren_content = protected_sql_1[paren_start:i+1]
            if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                placeholder = f"__SUBQUERY_{len(placeholders_1)}__"
                placeholders_1[placeholder] = paren_content
                print(f"  保护 {placeholder}")
                protected_sql_1 = protected_sql_1[:paren_start] + placeholder + protected_sql_1[i+1:]
                i = -1
                paren_depth = 0
                paren_start = -1
    i += 1

print(f"保护后的SQL: {protected_sql_1}")
print(f"占位符: {list(placeholders_1.keys())}")
print()

# ===== 第二层：递归格式化外层子查询 =====
print("【第二层】递归格式化外层子查询")
outer_subquery = placeholders_1['__SUBQUERY_0__']
print(f"外层子查询内容:")
print(outer_subquery)
print()

# 去掉外层括号
outer_subquery_inner = outer_subquery[1:-1]
print(f"去掉外层括号后:")
print(outer_subquery_inner)
print()

# 保护内层子查询
print("保护内层子查询:")
protected_sql_2 = outer_subquery_inner
placeholders_2 = {}
paren_depth = 0
paren_start = -1
i = 0

while i < len(protected_sql_2):
    if protected_sql_2[i] == '(':
        if paren_depth == 0:
            paren_start = i
        paren_depth += 1
    elif protected_sql_2[i] == ')':
        paren_depth -= 1
        if paren_depth == 0 and paren_start >= 0:
            paren_content = protected_sql_2[paren_start:i+1]
            if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                placeholder = f"__SUBQUERY_{len(placeholders_2)}__"
                placeholders_2[placeholder] = paren_content
                print(f"  保护 {placeholder}: {repr(paren_content)}")
                protected_sql_2 = protected_sql_2[:paren_start] + placeholder + protected_sql_2[i+1:]
                i = -1
                paren_depth = 0
                paren_start = -1
    i += 1

print(f"\n第二层保护后的SQL:")
print(protected_sql_2)
print(f"占位符: {list(placeholders_2.keys())}")
print()

# 解析第二层的WHERE子句
print("解析第二层的WHERE子句:")
clause_pattern = r'\b(WHERE)\b'
matches = list(re.finditer(clause_pattern, protected_sql_2, re.IGNORECASE))

if matches:
    match = matches[0]
    start = match.end()
    end = len(protected_sql_2)
    raw_content = protected_sql_2[start:end]
    clause_content = raw_content.strip().rstrip(',')

    print(f"WHERE子句内容: {repr(clause_content)}")

    # 查找占位符位置
    for placeholder, original in placeholders_2.items():
        if placeholder in clause_content:
            placeholder_pos = clause_content.find(placeholder)
            before_placeholder = clause_content[:placeholder_pos]
            print(f"  占位符: {placeholder}")
            print(f"  占位符前: {repr(before_placeholder)}")
            print(f"  占位符后: {repr(clause_content[placeholder_pos + len(placeholder):])}")
print()

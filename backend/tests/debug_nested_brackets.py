# -*- coding: utf-8 -*-
"""调试嵌套括号匹配"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 简化的测试案例
test_sql = """SELECT *
FROM (
    SELECT *
    FROM table1
    WHERE khzjdm NOT IN (
        SELECT DISTINCT khzjdm
        FROM table2
    )
) xyk;"""

print("=" * 80)
print("嵌套括号匹配调试")
print("=" * 80)
print("原始SQL:")
print(test_sql)
print()

# 手动分析括号深度
print("括号位置分析:")
for i, char in enumerate(test_sql):
    if char == '(' or char == ')':
        print(f"  位置 {i:3d}: {char}")
print()

# 模拟保护过程（正确的嵌套处理）
protected_sql = test_sql
placeholders = {}

def protect_subqueries_correctly(sql):
    """正确处理嵌套子查询的保护"""
    result = sql
    placeholders = {}
    paren_depth = 0
    paren_start = -1
    i = 0
    subquery_count = 0

    while i < len(result):
        if result[i] == '(':
            if paren_depth == 0:
                paren_start = i
            paren_depth += 1
        elif result[i] == ')':
            paren_depth -= 1
            if paren_depth == 0 and paren_start >= 0:
                paren_content = result[paren_start:i+1]
                if re.search(r'\bSELECT\b', paren_content, re.IGNORECASE):
                    placeholder = f"__SUBQUERY_{subquery_count}__"
                    subquery_count += 1
                    placeholders[placeholder] = paren_content
                    print(f"保护子查询 {subquery_count}:")
                    print(f"  起始位置: {paren_start}")
                    print(f"  结束位置: {i}")
                    print(f"  内容预览: {repr(paren_content[:80])}")
                    print()
                    result = result[:paren_start] + placeholder + result[i+1:]
                    # 重置以重新处理
                    i = -1
                    paren_depth = 0
                    paren_start = -1
        i += 1

    return result, placeholders

protected_sql, placeholders = protect_subqueries_correctly(test_sql)

print("保护后的SQL:")
print(protected_sql)
print()
print("占位符:")
for k, v in placeholders.items():
    print(f"  {k}: {len(v)} 字符")
    print(f"    内容: {repr(v[:100])}")
print()

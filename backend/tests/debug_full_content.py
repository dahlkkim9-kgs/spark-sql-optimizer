# -*- coding: utf-8 -*-
"""查看完整的占位符内容"""
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
print("完整占位符内容")
print("=" * 80)

# 手动分析
print("手动提取外层子查询:")
# FROM 后面的括号到最后的闭括号
outer_subquery = test_sql[14:129]  # 从第一个 ( 到最后一个 )
print(outer_subquery)
print()

print("外层子查询内容（去掉括号）:")
inner_content = outer_subquery[1:-1]  # 去掉外层括号
print(inner_content)
print()

print("内层子查询（IN 子查询）:")
# 查找 NOT IN 后的括号
not_in_pos = inner_content.find('NOT IN')
if not_in_pos > 0:
    # 从 NOT IN 后的 ( 开始
    inner_paren_start = inner_content.find('(', not_in_pos)
    # 匹配对应的闭括号
    depth = 0
    inner_paren_end = -1
    for i in range(inner_paren_start, len(inner_content)):
        if inner_content[i] == '(':
            depth += 1
        elif inner_content[i] == ')':
            depth -= 1
            if depth == 0:
                inner_paren_end = i
                break

    if inner_paren_end > 0:
        inner_subquery = inner_content[inner_paren_start:inner_paren_end+1]
        print(inner_subquery)
        print()
        print("内层子查询内容（去掉括号）:")
        print(inner_subquery[1:-1])

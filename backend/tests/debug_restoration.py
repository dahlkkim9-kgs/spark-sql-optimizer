# -*- coding: utf-8 -*-
"""调试占位符恢复过程"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 简化模拟占位符恢复过程
print("=" * 80)
print("占位符恢复过程调试")
print("=" * 80)
print()

# 模拟场景：外层子查询包含内层子查询
# 第一层保护后
clause_content = "WHERE col NOT IN __SUBQUERY_0__"
print(f"第一层 WHERE 子句内容: {repr(clause_content)}")

# 占位符对应的原始内容（外层子查询中的内层子查询部分）
original = "(\n        SELECT id FROM table2\n    )"
print(f"占位符原始内容: {repr(original)}")
print()

# 模拟递归格式化子查询（去掉外层括号后）
subquery_content = original[1:-1]  # 去掉括号
print(f"递归格式化的子查询内容: {repr(subquery_content)}")

# 假设格式化后的子查询（这是递归调用 _format_sql_structure 的结果）
# 这里的问题是：子查询已经被递归格式化了，但是返回的内容是什么？

# 让我们模拟：如果子查询内部没有其他占位符，那么格式化结果就是：
formatted_subquery = "SELECT id\nFROM table2"
print(f"格式化后的子查询: {repr(formatted_subquery)}")
print()

# 现在模拟替换过程（第 2599 行的逻辑）
# clause_content = clause_content.replace(placeholder, '(\n' + indented_subquery + '\n' + close_paren_indent + ')')

# 假设缩进是 4 个空格
subquery_indent = '    '
close_paren_indent = '   '

# 添加缩进
indented_subquery = '\n'.join(subquery_indent + line if line.strip() else line for line in formatted_subquery.split('\n'))
print(f"添加缩进后的子查询: {repr(indented_subquery)}")
print()

# 替换
replacement = '(\n' + indented_subquery + '\n' + close_paren_indent + ')'
print(f"替换内容: {repr(replacement)}")
print()

result = clause_content.replace('__SUBQUERY_0__', replacement)
print(f"替换结果: {repr(result)}")
print()

print("最终输出:")
print(result)
print()

# 现在让我查看实际问题：为什么会有重复的 "WHERE col NOT IN ("
# 问题可能在于：formatted_subquery 本身已经包含了 WHERE 子句？

print("=" * 80)
print("检查实际问题")
print("=" * 80)

# 让我检查：如果外层子查询是：
outer_subquery = """
    SELECT *
    FROM table1
    WHERE col NOT IN (
        SELECT id FROM table2
    )
"""

# 去掉外层括号后，内容应该是：
outer_subquery_inner = outer_subquery.strip()[1:-1]  # 去掉外层括号
print(f"外层子查询（去括号后）:\n{outer_subquery_inner}")
print()

# 当递归格式化这个子查询时，它会再次保护子查询
# 内层子查询被保护：
inner_subquery = "(SELECT id FROM table2)"
inner_placeholder = "__SUBQUERY_0__"

# 外层子查询变成：
protected_outer = outer_subquery_inner.replace(inner_subquery, inner_placeholder)
print(f"外层子查询（保护内层后）:\n{protected_outer}")
print()

# 然后格式化这个外层子查询...
# 假设格式化后是：
formatted_outer = """SELECT *
FROM table1
WHERE col NOT IN __SUBQUERY_0__"""

print(f"格式化后的外层子查询: {repr(formatted_outer)}")
print()

# 然后恢复占位符...
# 问题：formatted_outer 包含 `__SUBQUERY_0__`，这会被第一层的代码再次处理！
# 而第一层的 `__SUBQUERY_0__` 是外层子查询本身，不是内层子查询！

print("问题分析:")
print("- 第一层: __SUBQUERY_0__ = 外层子查询（包含 WHERE col NOT IN (内层子查询)）")
print("- 第二层: __SUBQUERY_0__ = 内层子查询")
print("- 第二层格式化后返回: 'WHERE col NOT IN __SUBQUERY_0__'")
print("- 第一层尝试恢复 __SUBQUERY_0__，但是看到的是 'WHERE col NOT IN __SUBQUERY_0__'")
print("- 这导致第一层的恢复逻辑出问题！")

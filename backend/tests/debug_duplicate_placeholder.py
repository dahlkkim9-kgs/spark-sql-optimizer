# -*- coding: utf-8 -*-
"""检查占位符是否被多次处理"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 模拟递归格式化后返回的内容
formatted_subquery_from_second_level = """SELECT *
FROM table1
WHERE col NOT IN __SUBQUERY_0__"""

print("=" * 80)
print("占位符多次处理检查")
print("=" * 80)
print(f"第二层格式化返回:\n{formatted_subquery_from_second_level}\n")

# 问题：这里返回的字符串包含 `__SUBQUERY_0__`！
# 这个 `__SUBQUERY_0__` 是第二层的占位符
# 但是当第一层尝试恢复占位符时，它会看到这个 `__SUBQUERY_0__`

print("问题分析:")
print("1. 第二层保护内层子查询: __SUBQUERY_0__")
print("2. 第二层格式化时，这个占位符应该被恢复")
print("3. 但是返回的字符串中仍然包含 __SUBQUERY_0__")
print("4. 这说明第二层的占位符恢复逻辑有问题！")
print()

# 让我检查第二层的占位符恢复
print("检查第二层的占位符恢复逻辑:")
print()

# 假设第二层的 clause_content 是：
second_level_clause_content = "col NOT IN __SUBQUERY_0__"
print(f"第二层的 WHERE 子句: {repr(second_level_clause_content)}")

# 第二层的占位符
second_level_placeholders = {
    '__SUBQUERY_0__': '(\n    SELECT id FROM table2\n)'
}

# 恢复占位符
for placeholder, original in second_level_placeholders.items():
    if placeholder in second_level_clause_content:
        print(f"  找到占位符: {placeholder}")
        print(f"  原始内容: {repr(original)}")

        # 假设格式化后的子查询
        formatted_inner = "SELECT id\nFROM table2"
        subquery_indent = '    '
        close_paren_indent = '   '

        indented_subquery = '\n'.join(subquery_indent + line if line.strip() else line for line in formatted_inner.split('\n'))
        replacement = '(\n' + indented_subquery + '\n' + close_paren_indent + ')'

        print(f"  替换内容: {repr(replacement)}")

        result = second_level_clause_content.replace(placeholder, replacement)
        print(f"  替换结果: {repr(result)}")

        # 这个结果应该是：'col NOT IN (\n    SELECT id\n    FROM table2\n   )'
        # 而不是包含 __SUBQUERY_0__

print()
print("结论:")
print("如果第二层的占位符正确恢复了，那么返回的字符串不应该包含 __SUBQUERY_0__")
print("如果返回的字符串包含 __SUBQUERY_0__，说明：")
print("  1. 第二层的占位符没有被恢复")
print("  2. 或者恢复后的字符串又被错误地处理了")

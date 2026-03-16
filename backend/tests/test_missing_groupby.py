# -*- coding: utf-8 -*-
"""
测试 INNER JOIN 中子查询丢失 GROUP BY 的问题
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
sys.path.insert(0, '../core')

from formatter_v4_fixed import format_sql_v4_fixed

# 测试 SQL：INNER JOIN 中的两个子查询
test_sql = """SELECT t1.department, t1.avg_salary, t2.max_salary
FROM (
    SELECT department, AVG(salary) as avg_salary
    FROM employees
    GROUP BY department
) t1
INNER JOIN (
    SELECT department, MAX(salary) as max_salary
    FROM employees
    GROUP BY department
) t2 ON t1.department = t2.department
WHERE t1.avg_salary > 50000;"""

print("=" * 80)
print("测试：INNER JOIN 中子查询的 GROUP BY 保留")
print("=" * 80)
print()
print("原始 SQL:")
print(test_sql)
print()

result = format_sql_v4_fixed(test_sql)

print("=" * 80)
print("格式化结果:")
print("=" * 80)
print(result)
print()

# 统计 GROUP BY
import re
original_count = len(re.findall(r'\bGROUP\s+BY\b', test_sql, re.IGNORECASE))
formatted_count = len(re.findall(r'\bGROUP\s+BY\b', result, re.IGNORECASE))

print("=" * 80)
print("GROUP BY 统计:")
print("=" * 80)
print(f"原始: {original_count}")
print(f"格式化: {formatted_count}")

if original_count == formatted_count:
    print("✅ GROUP BY 全部保留")
else:
    print(f"❌ GROUP BY 丢失了 {original_count - formatted_count} 个")

# 检查 t2 子查询
print()
print("t2 子查询检查:")
if re.search(r'\(\s*SELECT.*FROM employees\s*\)\s*t2', result, re.DOTALL):
    print("❌ t2 子查询中没有 GROUP BY")
elif re.search(r'\(\s*SELECT.*FROM employees.*GROUP BY.*\)\s*t2', result, re.DOTALL):
    print("✅ t2 子查询中有 GROUP BY")

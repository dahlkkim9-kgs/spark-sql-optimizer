# -*- coding: utf-8 -*-
"""测试嵌套子查询中的 IN 缩进问题"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, '../core')

from formatter_v4_fixed import format_sql_v4_fixed

# 用户报告的问题案例
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
print("嵌套子查询 IN 缩进测试")
print("=" * 80)
print("原始SQL:")
print(test_sql)
print()

result = format_sql_v4_fixed(test_sql)
print("格式化结果:")
print(result)
print()

# 分析缩进
lines = result.split('\n')
print("缩进分析:")
for i, line in enumerate(lines, 1):
    if line.strip():
        indent = len(line) - len(line.lstrip())
        print(f"行 {i:2d} ({indent:2d}空格): {line}")

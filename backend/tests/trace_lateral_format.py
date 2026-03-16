# -*- coding: utf-8 -*-
"""
跟踪 LATERAL VIEW 格式化流程
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
sys.path.insert(0, '../core')

from formatter_v4_fixed import format_sql_v4_fixed

# 测试：FROM 子查询 + LATERAL VIEW
test_sql = """SELECT * FROM (
    SELECT *
    FROM t
) alias LATERAL VIEW EXPLODE(x) y AS z LATERAL VIEW EXPLODE(y.a) b AS c"""

print("=" * 80)
print("测试：子查询后跟两个 LATERAL VIEW（压缩在一行）")
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

# 分析
result_lines = result.split('\n')
print("=" * 80)
print("逐行分析:")
print("=" * 80)
for i, line in enumerate(result_lines, 1):
    print(f"行 {i}: {repr(line)}")
print()

# 检查问题
lateral_lines = [i for i, line in enumerate(result_lines, 1) if 'LATERAL VIEW' in line]
print(f"LATERAL VIEW 出现在行: {lateral_lines}")

if len(lateral_lines) > 1:
    print("✅ LATERAL VIEW 分多行")
else:
    print("❌ LATERAL VIEW 被压缩")

# 检查第一个 LATERAL VIEW 后是否有第二个
for i, line in enumerate(result_lines):
    if line.count('LATERAL VIEW') > 1:
        print(f"❌ 第 {i+1} 行包含 {line.count('LATERAL VIEW')} 个 LATERAL VIEW")

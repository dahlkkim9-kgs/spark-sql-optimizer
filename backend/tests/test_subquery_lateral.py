# -*- coding: utf-8 -*-
"""
测试子查询后跟 LATERAL VIEW 的格式化问题
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
sys.path.insert(0, '../core')

from formatter_v4_fixed import format_sql_v4_fixed

# 测试SQL：子查询后跟 LATERAL VIEW
test_sql = """SELECT
    user_id,
    user_name,
    event_array
FROM (
    SELECT user_id,
           user_name,
           event_array
    FROM user_events
    WHERE event_date = '2024-03-13'
) base_data
LATERAL VIEW EXPLODE(event_array) exploded_events AS event_struct
LATERAL VIEW EXPLODE(
    exploded_events.event_struct.events
) exploded_individual AS event_type
GROUP BY
    user_id,
    user_name,
    event_type
HAVING COUNT(*) > 10;
"""

print("=" * 80)
print("测试：子查询后跟 LATERAL VIEW")
print("=" * 80)
print()
print("原始 SQL:")
print(test_sql)
print()

# 格式化
result = format_sql_v4_fixed(test_sql)

print("=" * 80)
print("格式化结果:")
print("=" * 80)
print(result)
print()

# 分析问题
result_lines = result.split('\n')
print("=" * 80)
print("分析结果:")
print("=" * 80)

# 查找问题行
for i, line in enumerate(result_lines, 1):
    if ') base_data' in line and 'LATERAL VIEW' in line:
        print(f"❌ 第 {i} 行: 闭括号后的别名和 LATERAL VIEW 在同一行")
        print(f"   {line}")

# 检查 LATERAL VIEW 行数
lateral_view_lines = [i for i, line in enumerate(result_lines, 1) if 'LATERAL VIEW' in line]
print(f"\nLATERAL VIEW 出现在行: {lateral_view_lines}")

if len(lateral_view_lines) == 2:
    print("✅ LATERAL VIEW 正确分成两行")
else:
    print(f"❌ LATERAL VIEW 行数不正确，应该是 2 行，实际 {len(lateral_view_lines)} 行")

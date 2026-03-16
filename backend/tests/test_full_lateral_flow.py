# -*- coding: utf-8 -*-
"""
测试完整的 LATERAL VIEW 处理流程
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
sys.path.insert(0, '../core')

from processors.advanced_transforms import AdvancedTransformsProcessor

# 测试 SQL
test_sql = """SELECT
    user_id,
    user_name,
    event_array
FROM base_data
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
print("完整 LATERAL VIEW 处理流程测试")
print("=" * 80)
print()
print("原始 SQL:")
print(test_sql)
print()

processor = AdvancedTransformsProcessor()
result = processor.process(test_sql, keyword_case='upper')

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
    if 'LATERAL VIEW' in line or 'GROUP BY' in line or 'HAVING' in line:
        print(f"行 {i}: {repr(line)}")
print()

# 检查问题
lateral_lines = [i for i, line in enumerate(result_lines, 1) if 'LATERAL VIEW' in line]
print(f"LATERAL VIEW 出现在行: {lateral_lines}")
if len(lateral_lines) == 2:
    print("✅ LATERAL VIEW 正确分成两行")
else:
    print(f"❌ LATERAL VIEW 行数不正确，应该是 2 行，实际 {len(lateral_lines)} 行")

# 检查 GROUP BY
group_by_lines = [i for i, line in enumerate(result_lines, 1) if 'GROUP BY' in line]
print(f"\nGROUP BY 出现在行: {group_by_lines}")
# 检查 GROUP BY 后面是否有多行
if group_by_lines:
    group_by_line_idx = group_by_lines[0] - 1
    # 检查 GROUP BY 后面的几行
    has_multiline_columns = False
    for j in range(group_by_line_idx + 1, min(group_by_line_idx + 5, len(result_lines))):
        if ',' in result_lines[j]:
            has_multiline_columns = True
            break
    if has_multiline_columns:
        print("✅ GROUP BY 是多行格式")
    else:
        print("❌ GROUP BY 是单行格式")
    # 显示 GROUP BY 相关的行
    print("\nGROUP BY 相关行:")
    for j in range(group_by_line_idx, min(group_by_line_idx + 5, len(result_lines))):
        print(f"  行 {j+1}: {result_lines[j]}")

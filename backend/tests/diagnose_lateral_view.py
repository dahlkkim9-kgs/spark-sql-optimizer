# -*- coding: utf-8 -*-
"""
诊断 LATERAL VIEW 格式化问题
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
sys.path.insert(0, '../core')

# 导入必要的模块
from processors.advanced_transforms import AdvancedTransformsProcessor

# 测试SQL片段
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
print("LATERAL VIEW 格式化诊断")
print("=" * 80)
print()
print("原始 SQL:")
print(test_sql)
print()

# 创建处理器
processor = AdvancedTransformsProcessor()

# 测试解析
print("=" * 80)
print("解析测试")
print("=" * 80)

# 提取 LATERAL VIEW 部分
lateral_part = """LATERAL VIEW EXPLODE(event_array) exploded_events AS event_struct
LATERAL VIEW EXPLODE(
    exploded_events.event_struct.events
) exploded_individual AS event_type
GROUP BY
    user_id,
    user_name,
    event_type
HAVING COUNT(*) > 10;
"""

print("输入 LATERAL 部分:")
print(lateral_part)
print()

# 调用解析方法
lateral_views, remaining_clauses = processor._parse_lateral_views_and_clauses(lateral_part)

print(f"解析到 {len(lateral_views)} 个 LATERAL VIEW:")
print()
for i, lv in enumerate(lateral_views, 1):
    print(f"LATERAL VIEW {i}:")
    print(f"  {repr(lv)}")
    print()

print(f"剩余子句:")
print(f"  {repr(remaining_clauses)}")
print()

# 测试格式化
print("=" * 80)
print("格式化测试")
print("=" * 80)

result = processor.process(test_sql, keyword_case='upper')
print("格式化结果:")
print(result)
print()

# 分析格式化结果
result_lines = result.split('\n')
print("格式化结果分析:")
print(f"  总行数: {len(result_lines)}")
for i, line in enumerate(result_lines, 1):
    if 'LATERAL VIEW' in line or 'GROUP BY' in line or 'HAVING' in line:
        print(f"  行 {i}: {line}")
print()

# 检查问题
lateral_view_count = sum(1 for line in result_lines if 'LATERAL VIEW' in line.upper())
print(f"LATERAL VIEW 行数: {lateral_view_count}")
if lateral_view_count < 2:
    print("❌ 问题: LATERAL VIEW 被压缩到少于2行")

# 检查是否在同一行
for i, line in enumerate(result_lines):
    if line.upper().count('LATERAL VIEW') > 1:
        print(f"❌ 问题: 第 {i+1} 行包含多个 LATERAL VIEW")
        print(f"  内容: {line}")

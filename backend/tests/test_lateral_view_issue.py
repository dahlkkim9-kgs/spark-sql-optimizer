# -*- coding: utf-8 -*-
"""
测试 LATERAL VIEW 格式化问题
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed

# 测试案例1: 简单的单个 LATERAL VIEW
test1 = """SELECT id, name FROM table1 LATERAL VIEW EXPLODE(array_col) exploded_table AS alias_col;"""

# 测试案例2: 多个 LATERAL VIEW
test2 = """SELECT
    user_id,
    user_name,
    event_type
FROM user_events
LATERAL VIEW EXPLODE(event_array) exploded_events AS event_struct
LATERAL VIEW EXPLODE(exploaded_events.event_struct.events) exploded_individual AS event_type;"""

# 测试案例3: 子查询 + LATERAL VIEW
test3 = """SELECT
    user_id,
    user_name,
    event_type
FROM (
    SELECT user_id, user_name, event_array
    FROM user_events
    WHERE event_date = '2024-03-13'
) base_data
LATERAL VIEW EXPLODE(event_array) exploded_events AS event_struct
LATERAL VIEW EXPLODE(exploded_events.event_struct.events) exploded_individual AS event_type;"""

def test_lateral_view_formatting():
    print("=" * 80)
    print("LATERAL VIEW 格式化测试")
    print("=" * 80)
    print()

    # 测试1
    print("【测试1】单个 LATERAL VIEW")
    print("-" * 80)
    print("原始SQL:")
    print(test1)
    print()
    result1 = format_sql_v4_fixed(test1)
    print("格式化结果:")
    print(result1)
    print()

    # 检查LATERAL VIEW是否在独立行
    lines1 = result1.split('\n')
    lateral_lines1 = [i for i, line in enumerate(lines1) if 'LATERAL VIEW' in line.upper()]
    print(f"LATERAL VIEW 所在行: {lateral_lines1}")
    print()

    # 测试2
    print("=" * 80)
    print("【测试2】多个 LATERAL VIEW")
    print("-" * 80)
    print("原始SQL:")
    print(test2)
    print()
    result2 = format_sql_v4_fixed(test2)
    print("格式化结果:")
    print(result2)
    print()

    # 检查LATERAL VIEW数量
    lateral_count2 = result2.upper().count('LATERAL VIEW')
    print(f"LATERAL VIEW 数量: {lateral_count2} (期望: 2)")
    print()

    # 测试3
    print("=" * 80)
    print("【测试3】子查询 + 多个 LATERAL VIEW")
    print("-" * 80)
    print("原始SQL:")
    print(test3)
    print()
    result3 = format_sql_v4_fixed(test3)
    print("格式化结果:")
    print(result3)
    print()

    # 检查LATERAL VIEW数量和位置
    lateral_count3 = result3.upper().count('LATERAL VIEW')
    print(f"LATERAL VIEW 数量: {lateral_count3} (期望: 2)")
    lines3 = result3.split('\n')
    for i, line in enumerate(lines3, 1):
        if 'LATERAL VIEW' in line.upper():
            print(f"  行 {i}: {line}")

if __name__ == "__main__":
    test_lateral_view_formatting()

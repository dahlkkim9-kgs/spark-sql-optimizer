# -*- coding: utf-8 -*-
"""
测试 UNION ALL 保留问题
"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed

# 测试案例1: 简单的 UNION ALL
test1 = """SELECT a FROM t1 UNION ALL SELECT b FROM t2;"""

# 测试案例2: UNION ALL + 嵌套
test2 = """--4. UNION + 嵌套 + CASE

SELECT
    product_id,
    product_name,
    sales_amount,
    'Q1' as quarter
FROM (
    SELECT
        p.product_id,
        p.product_name,
        SUM(oi.quantity * oi.unit_price) as sales_amount
    FROM products p
    INNER JOIN order_items oi ON p.product_id = oi.product_id
    WHERE o.order_date BETWEEN '2024-01-01' AND '2024-03-31'
    GROUP BY p.product_id, p.product_name
) q1_sales
WHERE sales_amount > 50000

UNION ALL

SELECT
    product_id,
    product_name,
    sales_amount,
    'Q2' as quarter
FROM (
    SELECT
        p.product_id,
        p.product_name,
        SUM(oi.quantity * oi.unit_price) as sales_amount
    FROM products p
    INNER JOIN order_items oi ON p.product_id = oi.product_id
    WHERE o.order_date BETWEEN '2024-04-01' AND '2024-06-30'
    GROUP BY p.product_id, p.product_name
) q2_sales;"""

# 测试案例3: 混合 UNION 和 UNION ALL
test3 = """SELECT a FROM t1 UNION ALL SELECT b FROM t2 UNION SELECT c FROM t3;"""

def test_union_all_preservation():
    print("=" * 80)
    print("UNION ALL 保留测试")
    print("=" * 80)
    print()

    # 测试1
    print("【测试1】简单的 UNION ALL")
    print("-" * 80)
    print("原始SQL:")
    print(test1)
    print()
    result1 = format_sql_v4_fixed(test1)
    print("格式化结果:")
    print(result1)
    print()

    # 检查 UNION ALL 是否保留
    union_all_count = result1.upper().count('UNION ALL')
    union_count = result1.upper().count('UNION')
    print(f"UNION ALL 数量: {union_all_count} (期望: 1)")
    print(f"UNION 数量: {union_count} (期望: 0，如果UNION ALL被保留)")
    print()

    if 'UNION ALL' not in result1.upper():
        print("❌ 问题: UNION ALL 被改成 UNION")
    else:
        print("✅ UNION ALL 正确保留")
    print()

    # 测试2
    print("=" * 80)
    print("【测试2】UNION ALL + 嵌套 + CASE（用户原始案例）")
    print("-" * 80)
    print("原始SQL:")
    print(test2)
    print()
    result2 = format_sql_v4_fixed(test2)
    print("格式化结果:")
    print(result2)
    print()

    # 检查 UNION ALL 是否保留
    union_all_count2 = result2.upper().count('UNION ALL')
    print(f"UNION ALL 数量: {union_all_count2} (期望: 1)")
    print()

    # 检查注释是否保留
    if '--4. UNION + 嵌套 + CASE' in result2:
        print("✅ 注释 '--4. UNION + 嵌套 + CASE' 保留")
    else:
        print("❌ 问题: 注释 '--4. UNION + 嵌套 + CASE' 丢失或被截断")
    print()

    # 测试3
    print("=" * 80)
    print("【测试3】混合 UNION 和 UNION ALL")
    print("-" * 80)
    print("原始SQL:")
    print(test3)
    print()
    result3 = format_sql_v4_fixed(test3)
    print("格式化结果:")
    print(result3)
    print()

    union_all_count3 = result3.upper().count('UNION ALL')
    union_count3 = result3.upper().replace('UNION ALL', '').count('UNION')
    print(f"UNION ALL 数量: {union_all_count3} (期望: 1)")
    print(f"UNION 数量: {union_count3} (期望: 1)")
    print()

if __name__ == "__main__":
    test_union_all_preservation()

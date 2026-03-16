# -*- coding: utf-8 -*-
"""
测试 UNION ALL + 嵌套子查询格式化问题
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys
import os

# 添加backend目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.formatter_v5 import format_sql_v5

# 原始SQL
original_sql = """--4. UNION + 嵌套 + CASE

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
    INNER JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_date BETWEEN '2024-01-01' AND '2024-03-31'
    GROUP BY p.product_id, p.product_name
    HAVING SUM(oi.quantity * oi.unit_price) > 10000
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
    INNER JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_date BETWEEN '2024-04-01' AND '2024-06-30'
    GROUP BY p.product_id, p.product_name
) q2_sales;"""

def test_union_all_comment_preservation():
    """测试 UNION ALL 和注释保留"""
    print("=" * 80)
    print("原始SQL:")
    print("=" * 80)
    print(original_sql)
    print()

    result = format_sql_v5(original_sql)

    print("=" * 80)
    print("格式化结果:")
    print("=" * 80)
    print(result)
    print()

    # 检查问题
    print("=" * 80)
    print("问题检查:")
    print("=" * 80)

    # 问题1: UNION ALL 是否被改成 UNION
    if "UNION ALL" not in result and "UNION" in result:
        print("❌ 问题1: UNION ALL 被错误地改成 UNION")
    else:
        print("✅ UNION ALL 保留正确")

    # 问题2: 注释是否完整保留
    if "--4. UNION + 嵌套 + CASE" not in result:
        print("❌ 问题2: 注释被截断或丢失")
        if "--4." in result:
            print("   发现: 注释变成了 '--4.'，丢失了 'UNION + 嵌套 + CASE'")
    else:
        print("✅ 注释保留完整")

    # 问题3: 缩进是否一致
    lines = result.split('\n')
    print()
    print("格式化后SQL结构:")
    for i, line in enumerate(lines[:50], 1):
        if line.strip():
            spaces = len(line) - len(line.lstrip())
            print(f"{i:3d} ({spaces:2d}空格): {line}")

if __name__ == "__main__":
    test_union_all_comment_preservation()

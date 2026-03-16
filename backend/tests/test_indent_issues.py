# -*- coding: utf-8 -*-
"""
测试嵌套缩进问题：IN子查询和JOIN ON条件
"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from formatter_v4_fixed import format_sql_v4_fixed

# 测试案例1: IN 子查询缩进问题
test1 = """SELECT customer_id, customer_name, total_amount
FROM customers c
WHERE customer_id IN (
    SELECT customer_id FROM orders
    WHERE order_date > '2024-01-01'
    AND total_amount > (
        SELECT AVG(total_amount) * 2 FROM orders
        WHERE order_date > '2024-01-01'
    )
)
ORDER BY total_amount DESC;"""

# 测试案例2: JOIN ON 条件缩进问题
test2 = """SELECT t1.department, t1.avg_salary, t2.max_salary
FROM (
    SELECT department, AVG(salary) as avg_salary
    FROM employees GROUP BY department
) t1
INNER JOIN (
    SELECT department, MAX(salary) as max_salary
    FROM employees GROUP BY department
) t2 ON t1.department = t2.department
LEFT JOIN employees t3 ON t1.department = t3.department
WHERE t1.avg_salary > 50000;"""

# 测试案例3: 复杂JOIN + IN子查询
test3 = """SELECT a.id, a.name, b.total
FROM table_a a
INNER JOIN table_b b ON a.id = b.a_id
LEFT JOIN table_c c ON b.id = c.b_id AND c.status = 'active'
WHERE a.id IN (
    SELECT id FROM table_d WHERE value > 100
)
AND a.category IN (1, 2, 3);"""

def test_indent_issues():
    print("=" * 80)
    print("嵌套缩进问题测试")
    print("=" * 80)
    print()

    tests = [
        ("IN 子查询缩进", test1),
        ("JOIN ON 条件缩进", test2),
        ("复杂JOIN + IN子查询", test3),
    ]

    for test_name, test_sql in tests:
        print(f"【测试】{test_name}")
        print("-" * 80)
        print("原始SQL:")
        print(test_sql)
        print()
        result = format_sql_v4_fixed(test_sql)
        print("格式化结果:")
        print(result)
        print()

        # 分析缩进问题
        lines = result.split('\n')
        print("缩进分析:")
        for i, line in enumerate(lines, 1):
            if line.strip():
                indent = len(line) - len(line.lstrip())
                # 显示关键行的缩进
                if any(keyword in line.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'IN', 'AND', 'ON', 'JOIN', 'LEFT', 'INNER']):
                    print(f"  行 {i:3d} ({indent:2d}空格): {line}")
        print()
        print("=" * 80)
        print()

if __name__ == "__main__":
    test_indent_issues()
